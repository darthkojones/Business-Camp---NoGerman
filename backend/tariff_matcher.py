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


# Persistent cache configuration
CACHE_FILE = "/app/data/tariff_cache.json"
_match_cache: Dict[str, TariffSuggestionResponse] = {}


def load_cache():
    """Load cache from disk"""
    global _match_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                # Convert JSON back to TariffSuggestionResponse objects
                for key, value in cache_data.items():
                    matches = [TariffMatchSchema(**match) for match in value.get('matches', [])]
                    _match_cache[key] = TariffSuggestionResponse(
                        cluster_id=value['cluster_id'],
                        cluster_name=value['cluster_name'],
                        matches=matches,
                        timestamp=value['timestamp']
                    )
                print(f"Loaded {len(_match_cache)} cached results from disk")
        except Exception as e:
            print(f"Error loading cache: {e}")
            _match_cache = {}
    else:
        print("No cache file found, starting with empty cache")


def save_cache():
    """Save cache to disk"""
    try:
        # Convert TariffSuggestionResponse objects to JSON-serializable dicts
        cache_data = {}
        for key, response in _match_cache.items():
            cache_data[key] = {
                'cluster_id': response.cluster_id,
                'cluster_name': response.cluster_name,
                'matches': [match.model_dump() for match in response.matches],
                'timestamp': response.timestamp
            }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(_match_cache)} cached results to disk")
    except Exception as e:
        print(f"Error saving cache: {e}")


# Load cache on module import
load_cache()


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
   - Only provide the most specific (10‑digit) HS codes. Avoid broad codes such as `7300000000`, `80`, or any code ending in more than four trailing zeros; these are too general.
   - If you are not confident about a precise 10‑digit code, explicitly state that you are "unsure" and, if possible, offer only the leading digits (e.g. "73" or "7308") as a prefix recommendation instead of a full code.
3. Suggest 3-5 best matching tariff codes in order of confidence
4. For each suggestion, provide:
   - The exact tariff code (goods_code) or a prefix with an "unsure" indication when uncertain
   - Confidence score (0.0 to 1.0)
   - Clear reasoning for why this code matches, or why a specific code could not be determined
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
            code = match_data.get("tariff_code", "").strip()
            reasoning = match_data.get("reasoning", "")
            # post‑process: flag broad or uncertain codes
            confidence = float(match_data.get("confidence_score", 0.0))
            if code:
                # if LLM inserted an explicit unsure flag
                if "unsure" in code.lower():
                    reasoning = f"[UNCERTAIN] {reasoning}"
                else:
                    # treat too-short codes as prefix suggestions
                    if len(code) < 10:
                        reasoning = f"[PREFIX SUGGESTION] {reasoning}"
                        confidence = min(confidence, 0.5)
                    # detect overly broad codes with many trailing zeros
                    stripped = code.rstrip('0')
                    trailing = len(code) - len(stripped)
                    if len(code) >= 6 and trailing >= 4:
                        reasoning = f"[BROAD CODE] {reasoning}"
                        confidence = min(confidence, 0.5)
            # skip entries that are too broad or not specific enough
            if code:
                # we consider a code specific only if it's at least 10 digits and
                # doesn't have 4+ trailing zeros (indicative of a chapter/heading)
                if not (len(code) >= 10 and not (trailing >= 4)):
                    # log or drop the code silently by continuing
                    print(f"Dropping non-specific tariff code suggestion: {code}")
                    continue
            else:
                # no code provided -> skip
                continue

            matches.append(TariffMatchSchema(
                tariff_code=code,
                confidence_score=confidence,
                reasoning=reasoning,
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
        
        # sort matches by confidence_score descending so highest is first
        matches.sort(key=lambda m: m.confidence_score or 0.0, reverse=True)
        
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
            save_cache()  # Persist to disk
        
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
    """Clear the matching cache both in memory and on disk"""
    global _match_cache
    _match_cache = {}
    
    # Delete cache file
    if os.path.exists(CACHE_FILE):
        try:
            os.remove(CACHE_FILE)
            print("Match cache cleared (memory and disk)")
        except Exception as e:
            print(f"Error deleting cache file: {e}")
    else:
        print("Match cache cleared (memory only, no file found)")
