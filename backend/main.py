from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, Base, engine
from models import Material, TariffCode
from schemas import MaterialSchema, TariffCodeSchema, ClusterSchema
from clustering import generate_clusters
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
def get_clusters():
    """
    Returns product clusters.
    Calls the underlying cluster generation logic.
    """
    return generate_clusters()

