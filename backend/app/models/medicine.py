"""
Medicine catalog models.
"""
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Text, Boolean, Numeric, Integer, Date, ForeignKey, ARRAY, JSONB, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Category(Base):
    """Medicine categories."""
    
    __tablename__ = "categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    icon_url = Column(String(500))
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    parent = relationship("Category", remote_side=[id], backref="children")
    medicines = relationship("Medicine", back_populates="category")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "icon_url": self.icon_url,
            "display_order": self.display_order,
            "is_active": self.is_active,
        }


class Medicine(Base):
    """Medicine/product catalog."""
    
    __tablename__ = "medicines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    generic_name = Column(String(255), index=True)
    description = Column(Text)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    manufacturer = Column(String(255))
    
    # Classification
    prescription_required = Column(Boolean, default=False, index=True)
    controlled_substance = Column(Boolean, default=False)
    controlled_schedule = Column(String(10))
    
    # Pricing
    price = Column(Numeric(10, 2), nullable=False)
    compare_at_price = Column(Numeric(10, 2))
    cost_price = Column(Numeric(10, 2))
    currency = Column(String(3), default="USD")
    
    # Physical
    weight_grams = Column(Numeric(8, 2))
    dimensions_cm = Column(String(50))
    
    # Storage
    storage_conditions = Column(String(100))
    temperature_requirements = Column(String(50))
    
    # Regulatory
    ndc_number = Column(String(11))
    upc_code = Column(String(12))
    batch_number = Column(String(50))
    expiry_date = Column(Date)
    
    # Media
    image_url = Column(String(500))
    additional_images = Column(ARRAY(String))
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_featured = Column(Boolean, default=False)
    requires_refrigeration = Column(Boolean, default=False)
    
    # SEO
    meta_title = Column(String(255))
    meta_description = Column(Text)
    slug = Column(String(255), unique=True)
    
    # Relationships
    category = relationship("Category", back_populates="medicines")
    details = relationship("MedicineDetails", back_populates="medicine", uselist=False)
    inventory = relationship("Inventory", back_populates="medicine", uselist=False)
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "sku": self.sku,
            "name": self.name,
            "generic_name": self.generic_name,
            "description": self.description,
            "category_id": str(self.category_id) if self.category_id else None,
            "category": self.category.to_dict() if self.category else None,
            "manufacturer": self.manufacturer,
            "prescription_required": self.prescription_required,
            "controlled_substance": self.controlled_substance,
            "price": float(self.price) if self.price else None,
            "compare_at_price": float(self.compare_at_price) if self.compare_at_price else None,
            "image_url": self.image_url,
            "is_active": self.is_active,
            "is_featured": self.is_featured,
            "slug": self.slug,
        }
    
    def to_detail_dict(self) -> dict:
        """Full details including related data."""
        data = self.to_dict()
        data["details"] = self.details.to_dict() if self.details else None
        data["inventory"] = self.inventory.to_dict() if self.inventory else None
        return data


class MedicineDetails(Base):
    """Detailed medicine information."""
    
    __tablename__ = "medicine_details"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medicine_id = Column(UUID(as_uuid=True), ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Composition
    active_ingredients = Column(JSONB)  # [{"name": "", "strength": ""}]
    inactive_ingredients = Column(ARRAY(String))
    dosage_form = Column(String(50))
    strength = Column(String(100))
    pack_size = Column(String(50))
    
    # Usage
    indications = Column(Text)
    contraindications = Column(Text)
    warnings = Column(Text)
    precautions = Column(Text)
    
    # Dosage
    adult_dosage = Column(Text)
    pediatric_dosage = Column(Text)
    geriatric_dosage = Column(Text)
    
    # Side effects
    common_side_effects = Column(ARRAY(String))
    serious_side_effects = Column(ARRAY(String))
    
    # Interactions
    drug_interactions = Column(ARRAY(String))
    food_interactions = Column(ARRAY(String))
    
    # Special populations
    pregnancy_category = Column(String(10))
    breastfeeding_notes = Column(Text)
    
    # Relationships
    medicine = relationship("Medicine", back_populates="details")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "active_ingredients": self.active_ingredients or [],
            "inactive_ingredients": self.inactive_ingredients or [],
            "dosage_form": self.dosage_form,
            "strength": self.strength,
            "pack_size": self.pack_size,
            "indications": self.indications,
            "contraindications": self.contraindications,
            "warnings": self.warnings,
            "precautions": self.precautions,
            "adult_dosage": self.adult_dosage,
            "pediatric_dosage": self.pediatric_dosage,
            "geriatric_dosage": self.geriatric_dosage,
            "common_side_effects": self.common_side_effects or [],
            "serious_side_effects": self.serious_side_effects or [],
            "drug_interactions": self.drug_interactions or [],
            "food_interactions": self.food_interactions or [],
            "pregnancy_category": self.pregnancy_category,
            "breastfeeding_notes": self.breastfeeding_notes,
        }


class DrugInteraction(Base):
    """Drug interaction database."""
    
    __tablename__ = "drug_interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medicine_id_1 = Column(UUID(as_uuid=True), ForeignKey("medicines.id"), nullable=False, index=True)
    medicine_id_2 = Column(UUID(as_uuid=True), ForeignKey("medicines.id"), nullable=False, index=True)
    interaction_type = Column(String(50), nullable=False, index=True)  # minor, moderate, major, contraindicated
    description = Column(Text, nullable=False)
    mechanism = Column(Text)
    management = Column(Text)
    references = Column(ARRAY(String))
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "medicine_id_1": str(self.medicine_id_1),
            "medicine_id_2": str(self.medicine_id_2),
            "interaction_type": self.interaction_type,
            "description": self.description,
            "mechanism": self.mechanism,
            "management": self.management,
        }
