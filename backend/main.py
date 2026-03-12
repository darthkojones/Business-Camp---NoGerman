from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, Base, engine
from models import Material, TariffCode
from schemas import MaterialSchema, TariffCodeSchema, ClusterSchema, TariffSuggestionResponse, EnrichedClusterSchema
from clustering import generate_clusters
from tariff_matcher import match_cluster_to_tariff, clear_cache
from typing import List, Optional
import pandas as pd
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


@app.post("/upload")
async def upload_files(
    materials_file: Optional[UploadFile] = File(None),
    customs_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Upload CSV files for materials and/or customs data.
    Processes and stores them in the database.
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
            
            # Clear existing materials
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
        
        # Process customs/tariff file
        if customs_file:
            if not customs_file.filename.endswith('.csv'):
                raise HTTPException(status_code=400, detail="Customs file must be a CSV file")
            
            content = await customs_file.read()
            df_tariffs = pd.read_csv(io.BytesIO(content), dtype=str)
            df_tariffs = df_tariffs.fillna("")
            
            # Clear existing tariff codes
            db.query(TariffCode).delete()
            
            # Insert new tariff codes
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

