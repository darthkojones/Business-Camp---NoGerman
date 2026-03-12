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
    indent: Optional[int] = None

    class Config:
        from_attributes = True

class ClusterItemSchema(BaseModel):
    item_id: str
    raw_description: str
    purchase_order_text: str
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


class EnrichedClusterSchema(BaseModel):
    """Cluster data enriched with tariff suggestions from LLM"""
    cluster_id: str
    cluster_name: str
    item_count: int
    common_attributes: List[str]
    items: List[ClusterItemSchema]
    tariff_suggestions: Optional[List[TariffMatchSchema]] = None
    suggestion_timestamp: Optional[str] = None
    status: str = "pending"  # pending, processing, completed, error


class ConfirmationRequest(BaseModel):
    """Request to confirm a tariff code assignment for a material"""
    material_number: str
    cluster_id: str
    assigned_tariff_code: str
    confidence_score: Optional[float] = None


class ConfirmationResponse(BaseModel):
    """Response after confirming a material assignment"""
    material_number: str
    assigned_tariff_code: str
    confirmed: bool
    message: str


class ExportItemSchema(BaseModel):
    """Schema for export data"""
    material_number: str
    short_text: str
    purchase_order_text: Optional[str] = None
    cluster_id: str
    cluster_name: str
    assigned_tariff_code: str
    confidence_score: Optional[float] = None
    confirmed_at: str
