import os
import json
import time
from typing import List, Dict, Optional
from datetime import datetime
from openai import OpenAI
from sqlalchemy.orm import Session
from schemas import ClusterSchema, TariffMatchSchema, TariffSuggestionResponse
from models import TariffCode

# Initialize OpenAI client
client = None

def get_openai_client():
    """Lazy initialization of OpenAI client"""
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        client = OpenAI(api_key=api_key)
    return client


# Simple in-memory cache for results (in production, use Redis or similar)
_match_cache: Dict[str, TariffSuggestionResponse] = {}


def get_section_mapping() -> Dict[str, str]:
    """Returns a mapping of product types to likely HS code sections"""
    return {
        "O-Ring": "VII - Plastics and articles thereof; rubber and articles thereof (Chapter 40)",
        "Wellendichtring": "VII - Plastics and articles thereof; rubber and articles thereof (Chapter 40)",
        "Schraube": "XV - Base metals and articles of base metal (Chapter 73)",
        "Mutter": "XV - Base metals and articles of base metal (Chapter 73)",
        "Servomotor": "XVI - Machinery and mechanical appliances; electrical equipment (Chapter 85)",
        "GT-Motor": "XVI - Machinery and mechanical appliances; electrical equipment (Chapter 85)",
        "PN-Zylinder": "XVI - Machinery and mechanical appliances; electrical equipment (Chapter 84)",
        "Kettenrad": "XV - Base metals and articles of base metal (Chapter 73)",
        "Lager": "XV - Base metals and articles of base metal (Chapter 84 - bearings)",
    }


def get_relevant_tariff_codes(db: Session, cluster_name: str, limit: int = 50) -> List[TariffCode]:
    """
    Retrieve relevant tariff codes from database based on cluster type.
    This filters to reduce the search space for the LLM.
    """
    section_mapping = get_section_mapping()
    
    # Get section hint
    section_hint = section_mapping.get(cluster_name, "")
    
    # Build search query based on product family
    query = db.query(TariffCode)
    
    # Section-based filtering
    if "rubber" in section_hint.lower() or cluster_name in ["O-Ring", "Wellendichtring"]:
        # Section VII - Rubber articles typically start with 40
        query = query.filter(TariffCode.goods_code.like('40%'))
    elif cluster_name in ["Schraube", "Mutter", "Kettenrad"]:
        # Metal fasteners - Chapter 73
        query = query.filter(TariffCode.goods_code.like('73%'))
    elif cluster_name in ["Servomotor", "GT-Motor"]:
        # Electric motors - Chapter 85
        query = query.filter(TariffCode.goods_code.like('85%'))
    elif cluster_name in ["PN-Zylinder"]:
        # Pneumatic cylinders - Chapter 84
        query = query.filter(TariffCode.goods_code.like('84%'))
    elif cluster_name in ["Lager"]:
        # Bearings - Chapter 84
        query = query.filter(TariffCode.goods_code.like('84%'))
    
    return query.limit(limit).all()


def build_matching_prompt(cluster: ClusterSchema, tariff_codes: List[TariffCode]) -> str:
    """
    Constructs the prompt for OpenAI to match clusters to tariff codes.
    """
    
    # Get sample items (limit to 5 for brevity)
    sample_items = cluster.items[:5]
    sample_descriptions = [item.raw_description for item in sample_items]
    
    # Build tariff code reference
    tariff_reference = []
    for tc in tariff_codes[:30]:  # Limit context size
        tariff_reference.append(f"- {tc.goods_code}: {tc.description}")
    
    prompt = f"""You are an expert in Harmonized System (HS) tariff code classification for international trade.

**Task**: Analyze the following product cluster and suggest the top 3-5 most appropriate HS tariff codes.

**Product Cluster Information:**
- Cluster Name: {cluster.cluster_name}
- Number of Items: {cluster.item_count}
- Common Attributes: {', '.join(cluster.common_attributes) if cluster.common_attributes else 'None identified'}

**Sample Product Descriptions:**
{chr(10).join(f"{i+1}. {desc}" for i, desc in enumerate(sample_descriptions))}

**Available Tariff Codes (filtered by relevance):**
{chr(10).join(tariff_reference[:30])}

**Instructions:**
1. Analyze the product characteristics, materials, and usage
2. Consider the HS code hierarchy and specificity
3. Suggest 3-5 best matching tariff codes in order of confidence
4. For each suggestion, provide:
   - The exact tariff code (goods_code)
   - Confidence score (0.0 to 1.0)
   - Clear reasoning for why this code matches
   - Section information

**Response Format (JSON only, no markdown):**
{{
  "matches": [
    {{
      "tariff_code": "CODE",
      "confidence_score": 0.95,
      "reasoning": "Explanation of why this code fits",
      "section_info": "Section X - Category Name"
    }}
  ]
}}

Respond with valid JSON only."""
    
    return prompt


def parse_llm_response(response_text: str) -> List[TariffMatchSchema]:
    """
    Parse the LLM response into structured TariffMatchSchema objects.
    """
    try:
        # Remove markdown code blocks if present
        response_text = response_text.strip()
        if response_text.startswith("```"):
            # Extract JSON from code block
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(response_text)
        matches = []
        
        for match_data in data.get("matches", []):
            matches.append(TariffMatchSchema(
                tariff_code=match_data.get("tariff_code", ""),
                confidence_score=float(match_data.get("confidence_score", 0.0)),
                reasoning=match_data.get("reasoning", ""),
                section_info=match_data.get("section_info"),
                description=match_data.get("description")
            ))
        
        return matches
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM response: {e}")
        print(f"Response text: {response_text}")
        # Return a fallback response
        return [TariffMatchSchema(
            tariff_code="UNKNOWN",
            confidence_score=0.0,
            reasoning=f"Failed to parse LLM response: {str(e)}",
            section_info="Error"
        )]
    except Exception as e:
        print(f"Error parsing response: {e}")
        return [TariffMatchSchema(
            tariff_code="ERROR",
            confidence_score=0.0,
            reasoning=f"Error: {str(e)}",
            section_info="Error"
        )]


def match_cluster_to_tariff(
    cluster: ClusterSchema,
    db: Session,
    use_cache: bool = True,
    model: str = "gpt-4o-mini"  # Use gpt-4o-mini for cost efficiency, or gpt-4 for better accuracy
) -> TariffSuggestionResponse:
    """
    Main function to match a cluster to tariff codes using OpenAI.
    
    Args:
        cluster: The product cluster to classify
        db: Database session
        use_cache: Whether to use cached results
        model: OpenAI model to use (gpt-4o-mini, gpt-4, gpt-3.5-turbo)
    
    Returns:
        TariffSuggestionResponse with ranked matches
    """
    
    # Check cache first
    cache_key = f"{cluster.cluster_id}_{cluster.cluster_name}"
    if use_cache and cache_key in _match_cache:
        print(f"Returning cached result for {cache_key}")
        return _match_cache[cache_key]
    
    try:
        # Get relevant tariff codes from database
        tariff_codes = get_relevant_tariff_codes(db, cluster.cluster_name)
        
        if not tariff_codes:
            # Fallback: get any tariff codes if filtering returns nothing
            tariff_codes = db.query(TariffCode).limit(50).all()
        
        # Build the prompt
        prompt = build_matching_prompt(cluster, tariff_codes)
        
        # Call OpenAI API
        openai_client = get_openai_client()
        
        print(f"Calling OpenAI API with model: {model}")
        start_time = time.time()
        
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert in HS tariff code classification. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent results
            max_tokens=1500
        )
        
        elapsed_time = time.time() - start_time
        print(f"OpenAI API call completed in {elapsed_time:.2f}s")
        
        # Parse the response
        response_text = response.choices[0].message.content
        matches = parse_llm_response(response_text)
        
        # Create the final response
        result = TariffSuggestionResponse(
            cluster_id=cluster.cluster_id,
            cluster_name=cluster.cluster_name,
            matches=matches,
            timestamp=datetime.now().isoformat()
        )
        
        # Cache the result
        if use_cache:
            _match_cache[cache_key] = result
        
        return result
        
    except Exception as e:
        print(f"Error in match_cluster_to_tariff: {e}")
        # Return error response
        return TariffSuggestionResponse(
            cluster_id=cluster.cluster_id,
            cluster_name=cluster.cluster_name,
            matches=[TariffMatchSchema(
                tariff_code="ERROR",
                confidence_score=0.0,
                reasoning=f"Error during matching: {str(e)}",
                section_info="Error"
            )],
            timestamp=datetime.now().isoformat()
        )


def clear_cache():
    """Clear the matching cache"""
    global _match_cache
    _match_cache = {}
    print("Match cache cleared")
