from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, Base, engine
from models import Material, TariffCode
from schemas import MaterialSchema, TariffCodeSchema, ClusterSchema, TariffSuggestionResponse, EnrichedClusterSchema
from clustering import generate_clusters
from tariff_matcher import match_cluster_to_tariff, clear_cache
from typing import List, Optional

app = FastAPI(title="Harmonized Tariff Codes Classification API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/materials", response_model=List[MaterialSchema])
def get_all_materials(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    materials = db.query(Material).offset(skip).limit(limit).all()
    return materials

@app.get("/tariffs", response_model=List[TariffCodeSchema])
def get_tariffs(skip: int = 0, limit: int = 200, search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(TariffCode)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(TariffCode.goods_code.ilike(search_fmt) | TariffCode.description.ilike(search_fmt))
    tariffs = query.offset(skip).limit(limit).all()
    return tariffs

@app.get("/clusters", response_model=List[ClusterSchema])
def get_clusters(db: Session = Depends(get_db)):
    """
    Returns product clusters.
    Calls the underlying cluster generation logic.
    """
    return generate_clusters(db)


@app.get("/clusters/enriched", response_model=List[EnrichedClusterSchema])
def get_enriched_clusters(
    auto_generate: bool = Query(True, description="Automatically generate tariff suggestions for all clusters"),
    model: Optional[str] = Query("gpt-4o-mini", description="OpenAI model to use"),
    db: Session = Depends(get_db)
):
    """
    Returns product clusters enriched with tariff suggestions.
    This is the main endpoint for the detailed results view.
    
    - **auto_generate**: If True, automatically generates tariff suggestions for all clusters
    - **model**: OpenAI model to use (default: gpt-4o-mini)
    
    Returns clusters with their items and LLM-suggested tariff codes.
    """
    clusters = generate_clusters(db)
    enriched_clusters = []
    
    for cluster in clusters:
        enriched = EnrichedClusterSchema(
            cluster_id=cluster.cluster_id,
            cluster_name=cluster.cluster_name,
            item_count=cluster.item_count,
            common_attributes=cluster.common_attributes,
            items=cluster.items,
            status="pending"
        )
        
        if auto_generate:
            try:
                # Generate tariff suggestions
                suggestions = match_cluster_to_tariff(
                    cluster=cluster,
                    db=db,
                    use_cache=True,
                    model=model
                )
                enriched.tariff_suggestions = suggestions.matches
                enriched.suggestion_timestamp = suggestions.timestamp
                enriched.status = "completed"
            except Exception as e:
                print(f"Error generating suggestions for {cluster.cluster_id}: {e}")
                enriched.status = "error"
                enriched.tariff_suggestions = []
        
        enriched_clusters.append(enriched)
    
    return enriched_clusters


@app.post("/clusters/{cluster_id}/suggest-tariffs", response_model=TariffSuggestionResponse)
def suggest_tariffs_for_cluster(
    cluster_id: str,
    model: Optional[str] = Query("gpt-4o-mini", description="OpenAI model to use (gpt-4o-mini, gpt-4, gpt-3.5-turbo)"),
    use_cache: bool = Query(True, description="Use cached results if available"),
    db: Session = Depends(get_db)
):
    """
    Suggest appropriate tariff codes for a specific cluster using OpenAI.
    
    - **cluster_id**: The ID of the cluster (e.g., CL-001)
    - **model**: OpenAI model to use (default: gpt-4o-mini for cost efficiency)
    - **use_cache**: Whether to use cached results (default: True)
    
    Returns ranked tariff code suggestions with confidence scores and reasoning.
    """
    # Get all clusters
    clusters = generate_clusters(db)
    
    # Find the specific cluster
    target_cluster = None
    for cluster in clusters:
        if cluster.cluster_id == cluster_id:
            target_cluster = cluster
            break
    
    if not target_cluster:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")
    
    # Call the matching service
    try:
        result = match_cluster_to_tariff(
            cluster=target_cluster,
            db=db,
            use_cache=use_cache,
            model=model
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during tariff matching: {str(e)}")


@app.post("/clusters/clear-cache")
def clear_matching_cache():
    """
    Clear the tariff matching cache.
    Useful when you want to force fresh API calls.
    """
    clear_cache()
    return {"message": "Cache cleared successfully"}

