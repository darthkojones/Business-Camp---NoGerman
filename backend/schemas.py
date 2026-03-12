from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class MaterialSchema(BaseModel):
    id: int
    material_number: str
    short_text: Optional[str] = None
    purchase_order_text: Optional[str] = None
    is_classified: bool
    tariff_code_id: Optional[int] = None

    class Config:
        from_attributes = True

class TariffCodeSchema(BaseModel):
    id: int
    goods_code: str
    description: Optional[str] = None
    language: Optional[str] = None

    class Config:
        from_attributes = True

class ClusterItemSchema(BaseModel):
    item_id: str
    raw_description: str
    parsed_data: Dict[str, Any]

class ClusterSchema(BaseModel):
    cluster_id: str
    cluster_name: str
    item_count: int
    common_attributes: List[str]
    items: List[ClusterItemSchema]


class TariffMatchSchema(BaseModel):
    tariff_code: str
    confidence_score: float  # 0.0 to 1.0
    reasoning: str
    section_info: Optional[str] = None
    description: Optional[str] = None


class DistributionItemSchema(BaseModel):
    tariff_code_id: Optional[int] = None
    goods_code: Optional[str] = None
    description: Optional[str] = None
    count: int

class BulkUpdateMaterialSchema(BaseModel):
    material_ids: List[int]
    new_tariff_code_id: int

class TariffSuggestionResponse(BaseModel):
    cluster_id: str
    cluster_name: str
    matches: List[TariffMatchSchema]
    timestamp: str
