from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class TariffCode(Base):
    __tablename__ = "tariff_codes"

    id = Column(Integer, primary_key=True, index=True)
    goods_code = Column(String, index=True)
    description = Column(Text)
    language = Column(String)
    indent = Column(Integer)
    start_date = Column(String)
    end_date = Column(String)

    materials = relationship("Material", back_populates="tariff_code")


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    material_number = Column(String, unique=True, index=True)
    short_text = Column(Text)
    purchase_order_text = Column(Text)
    is_classified = Column(Boolean, default=False)
    
    tariff_code_id = Column(Integer, ForeignKey("tariff_codes.id"), nullable=True)
    tariff_code = relationship("TariffCode", back_populates="materials")
