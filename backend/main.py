from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, Base, engine
from models import Material, TariffCode
from schemas import MaterialSchema, TariffCodeSchema, ClusterSchema, TariffSuggestionResponse, DistributionItemSchema, BulkUpdateMaterialSchema
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
def get_all_materials(skip: int = 0, limit: int = 200, tariff_code_id: Optional[int] = None, is_unclassified: Optional[bool] = None, db: Session = Depends(get_db)):
    query = db.query(Material)
    if is_unclassified is True:
        query = query.filter(Material.tariff_code_id.is_(None))
    elif tariff_code_id is not None:
        query = query.filter(Material.tariff_code_id == tariff_code_id)
    
    materials = query.offset(skip).limit(limit).all()
    return materials

@app.get("/tariffs", response_model=List[TariffCodeSchema])
def get_tariffs(skip: int = 0, limit: int = 200, search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(TariffCode)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(TariffCode.goods_code.ilike(search_fmt) | TariffCode.description.ilike(search_fmt))
    tariffs = query.offset(skip).limit(limit).all()
    return tariffs

@app.get("/tariffs/hierarchy", response_model=List[TariffCodeSchema])
def get_tariffs_hierarchy(parent_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Returns the next level of the tariff hierarchy.
    - If parent_id is None, return top-level categories (indent=2).
    - If parent_id is provided, return its immediate children.
    """
    if parent_id is None:
        return db.query(TariffCode).filter(TariffCode.indent == 2).order_by(TariffCode.id).all()
    
    parent = db.query(TariffCode).filter(TariffCode.id == parent_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent tariff code not found")
    
    # Find children: items that follow the parent and have indent = parent.indent + 2
    # But we need to make sure we don't jump into a different branch.
    # We look at all items after the parent.
    # We stop when we hit an item with indent <= parent.indent.
    
    all_following = db.query(TariffCode).filter(TariffCode.id > parent.id).order_by(TariffCode.id).all()
    
    immediate_children = []
    target_indent = parent.indent + 2
    
    # Sometimes hierarchy jumps (e.g. 4 -> 8 if 6 is missing or structure is weird)
    # But usually it's +2.
    # To be safe, we find the MINIMUM indent that is > parent.indent among following items.
    
    found_any_child_indent = None
    for item in all_following:
        if item.indent <= parent.indent:
            break
        
        if found_any_child_indent is None or item.indent < found_any_child_indent:
             found_any_child_indent = item.indent
             
    if found_any_child_indent is None:
        return []
        
    # Now collect all items with that specific indent within this branch
    for item in all_following:
        if item.indent <= parent.indent:
            break
        if item.indent == found_any_child_indent:
            immediate_children.append(item)
            
    return immediate_children

from sqlalchemy import func

@app.get("/analytics/distribution", response_model=List[DistributionItemSchema])
def get_distribution(db: Session = Depends(get_db)):
    """
    Returns the distribution of materials across tariff codes, including unclassified ones.
    """
    results = db.query(
        Material.tariff_code_id,
        TariffCode.goods_code,
        TariffCode.description,
        func.count(Material.id).label('count')
    ).outerjoin(TariffCode, Material.tariff_code_id == TariffCode.id)\
     .group_by(Material.tariff_code_id, TariffCode.goods_code, TariffCode.description)\
     .all()

    distribution = []
    for row in results:
        distribution.append({
            "tariff_code_id": row.tariff_code_id,
            "goods_code": row.goods_code,
            "description": row.description,
            "count": row.count
        })
    
    # Sort unclassified first, then by count descending
    distribution.sort(key=lambda x: (x["tariff_code_id"] is not None, -x["count"]))
    return distribution

@app.patch("/materials/bulk-update")
def bulk_update_materials(request: BulkUpdateMaterialSchema, db: Session = Depends(get_db)):
    """
    Bulk update materials with a new tariff code.
    """
    tariff = db.query(TariffCode).filter(TariffCode.id == request.new_tariff_code_id).first()
    if not tariff:
        raise HTTPException(status_code=404, detail="Tariff code not found")

    materials = db.query(Material).filter(Material.id.in_(request.material_ids)).all()
    if not materials:
        raise HTTPException(status_code=404, detail="No materials found matching provided IDs")

    for material in materials:
        material.tariff_code_id = request.new_tariff_code_id
        material.is_classified = True
    
    db.commit()
    return {"message": f"Successfully updated {len(materials)} materials"}

@app.get("/clusters", response_model=List[ClusterSchema])
def get_clusters(db: Session = Depends(get_db)):
    """
    Returns product clusters.
    Calls the underlying cluster generation logic.
    """
    return generate_clusters(db)


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

