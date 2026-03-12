from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

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
    
    confirmations = relationship("UserConfirmation", back_populates="material", cascade="all, delete-orphan")


class UserConfirmation(Base):
    """Track user-confirmed tariff code assignments"""
    __tablename__ = "user_confirmations"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    material_number = Column(String, index=True)
    cluster_id = Column(String)
    assigned_tariff_code = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=True)
    confirmed_at = Column(DateTime, default=datetime.utcnow)
    confirmed_by = Column(String, default="user")
    
    material = relationship("Material", back_populates="confirmations")
