from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, Base, engine
from models import Material, TariffCode, UserConfirmation
from schemas import MaterialSchema, TariffCodeSchema, ClusterSchema, TariffSuggestionResponse, EnrichedClusterSchema, ConfirmationRequest, ConfirmationResponse, ExportItemSchema, DistributionItemSchema, BulkUpdateMaterialSchema
from clustering import generate_clusters
from tariff_matcher import match_cluster_to_tariff, clear_cache
from typing import List, Optional
import pandas as pd
import io
from datetime import datetime
import io

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

@app.get("/tariffs/count")
def get_tariffs_count(db: Session = Depends(get_db)):
    """Return the total number of tariff codes in the database."""
    total = db.query(TariffCode).count()
    return {"count": total}

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


@app.post("/upload")
async def upload_files(
    materials_file: Optional[UploadFile] = File(None),
    customs_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Upload CSV files for materials and/or customs data.
    
    *Materials* file is required for clustering.
    *Tariff/customs* file is optional since a default dataset (`data/CostumsData.csv`) is seeded
    into the database on startup; uploading new tariff data will replace the existing entries.

    Processes and stores the provided files in the database.
    """
    materials_count = 0
    tariffs_count = 0
    
    try:
        # Process materials file
        if materials_file:
            if not materials_file.filename.endswith('.csv'):
                raise HTTPException(status_code=400, detail="Materials file must be a CSV file")
            
            content = await materials_file.read()
            df_materials = pd.read_csv(io.BytesIO(content), dtype=str)
            df_materials = df_materials.fillna("")
            
            # Clear existing materials (delete confirmations first due to foreign key constraints)
            db.query(UserConfirmation).delete()
            db.query(Material).delete()
            
            # Insert new materials
            materials_to_insert = []
            for _, row in df_materials.iterrows():
                material_number = row.get('Material number', row.get('Materialnummer', ''))
                short_text = row.get('Short text', row.get('Kurztext', ''))
                po_text = row.get('Purchase order text', row.get('Bestelltext', ''))
                
                materials_to_insert.append(Material(
                    material_number=material_number,
                    short_text=short_text,
                    purchase_order_text=po_text,
                    is_classified=False
                ))
            
            db.bulk_save_objects(materials_to_insert)
            db.commit()
            materials_count = len(materials_to_insert)
            print(f"Uploaded {materials_count} materials")
        
        # Process customs/tariff file if one is provided
        if customs_file:
            if not customs_file.filename.endswith('.csv'):
                raise HTTPException(status_code=400, detail="Customs file must be a CSV file")
            
            content = await customs_file.read()
            df_tariffs = pd.read_csv(io.BytesIO(content), dtype=str)
            df_tariffs = df_tariffs.fillna("")
            
            # Clear existing tariff codes and insert new ones
            db.query(TariffCode).delete()
            
            tariffs_to_insert = []
            for _, row in df_tariffs.iterrows():
                tariffs_to_insert.append(TariffCode(
                    goods_code=row.get('Goods code', row.get('goods_code', '')),
                    description=row.get('Description', row.get('description', '')),
                    language=row.get('Language', row.get('language', 'EN')),
                    start_date=row.get('Start date', row.get('start_date', '')),
                    end_date=row.get('End date', row.get('end_date', ''))
                ))
            
            db.bulk_save_objects(tariffs_to_insert)
            db.commit()
            tariffs_count = len(tariffs_to_insert)
            print(f"Uploaded {tariffs_count} tariff codes")
        else:
            # no customs file uploaded, report existing tariff count from DB
            tariffs_count = db.query(TariffCode).count()
        
        return {
            "message": "Files uploaded successfully",
            "materials_count": materials_count,
            "tariffs_count": tariffs_count
        }
    
    except Exception as e:
        db.rollback()
        print(f"Error uploading files: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading files: {str(e)}")


@app.post("/process")
def process_and_analyze(db: Session = Depends(get_db)):
    """
    Trigger the clustering and LLM analysis process.
    This generates clusters from materials and creates tariff suggestions.
    """
    try:
        # Generate clusters
        clusters = generate_clusters(db)
        
        if not clusters:
            raise HTTPException(status_code=400, detail="No materials found to cluster. Please upload materials first.")
        
        # Generate tariff suggestions for all clusters
        analyzed_count = 0
        for cluster in clusters:
            try:
                match_cluster_to_tariff(
                    cluster=cluster,
                    db=db,
                    use_cache=True,
                    model="gpt-4o-mini"
                )
                analyzed_count += 1
            except Exception as e:
                print(f"Error analyzing cluster {cluster.cluster_id}: {e}")
                # Continue with next cluster even if one fails
        
        return {
            "message": "Processing completed",
            "clusters_count": len(clusters),
            "analyzed_count": analyzed_count
        }
    
    except Exception as e:
        print(f"Error during processing: {e}")
        raise HTTPException(status_code=500, detail=f"Error during processing: {str(e)}")


@app.post("/confirmations", response_model=ConfirmationResponse)
def confirm_material_assignment(
    confirmation: ConfirmationRequest,
    db: Session = Depends(get_db)
):
    """
    Confirm and save a tariff code assignment for a material.
    This creates a permanent record of the user's selection.
    """
    try:
        # Find the material
        material = db.query(Material).filter(
            Material.material_number == confirmation.material_number
        ).first()
        
        if not material:
            raise HTTPException(
                status_code=404,
                detail=f"Material {confirmation.material_number} not found"
            )
        
        # Check if there's already a confirmation for this material
        existing = db.query(UserConfirmation).filter(
            UserConfirmation.material_number == confirmation.material_number
        ).first()
        
        if existing:
            # Update existing confirmation
            existing.assigned_tariff_code = confirmation.assigned_tariff_code
            existing.cluster_id = confirmation.cluster_id
            existing.confidence_score = confirmation.confidence_score
            existing.confirmed_at = datetime.utcnow()
        else:
            # Create new confirmation
            new_confirmation = UserConfirmation(
                material_id=material.id,
                material_number=confirmation.material_number,
                cluster_id=confirmation.cluster_id,
                assigned_tariff_code=confirmation.assigned_tariff_code,
                confidence_score=confirmation.confidence_score
            )
            db.add(new_confirmation)
        
        # Mark material as classified
        material.is_classified = True
        
        # also update the material's tariff_code_id so that overview reflects the
        # user selection. look up the TariffCode row by goods_code (8‑digit HS code)
        # and assign its id; if no match exists we leave it unset.
        if confirmation.assigned_tariff_code:
            tariff = db.query(TariffCode).filter(
                TariffCode.goods_code == confirmation.assigned_tariff_code
            ).first()
            if tariff:
                material.tariff_code_id = tariff.id
            else:
                # supply a warning in the log if the code didn't match
                print(f"Warning: assigned tariff code {confirmation.assigned_tariff_code} not found in table")
        
        db.commit()
        
        return ConfirmationResponse(
            material_number=confirmation.material_number,
            assigned_tariff_code=confirmation.assigned_tariff_code,
            confirmed=True,
            message="Tariff assignment confirmed successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error confirming assignment: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error confirming assignment: {str(e)}"
        )


@app.get("/confirmations", response_model=List[ExportItemSchema])
def get_confirmed_items(db: Session = Depends(get_db)):
    """
    Get all confirmed material-tariff assignments.
    Returns data ready for export.
    """
    try:
        confirmations = db.query(UserConfirmation).all()
        
        export_items = []
        for conf in confirmations:
            material = db.query(Material).filter(Material.id == conf.material_id).first()
            if material:
                # Find cluster name by re-generating clusters
                clusters = generate_clusters(db)
                cluster_name = ""
                for cluster in clusters:
                    if cluster.cluster_id == conf.cluster_id:
                        cluster_name = cluster.cluster_name
                        break
                
                export_items.append(ExportItemSchema(
                    material_number=conf.material_number,
                    short_text=material.short_text or "",
                    purchase_order_text=material.purchase_order_text,
                    cluster_id=conf.cluster_id,
                    cluster_name=cluster_name,
                    assigned_tariff_code=conf.assigned_tariff_code,
                    confidence_score=conf.confidence_score,
                    confirmed_at=conf.confirmed_at.isoformat()
                ))
        
        return export_items
    
    except Exception as e:
        print(f"Error retrieving confirmations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving confirmations: {str(e)}"
        )


@app.delete("/confirmations")
def clear_all_confirmations(db: Session = Depends(get_db)):
    """Clear all confirmed assignments (for testing/reset purposes)"""
    try:
        db.query(UserConfirmation).delete()
        db.commit()
        return {"message": "All confirmations cleared"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

