"""
Prescription management models.
"""
import uuid
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Text, Date, DateTime, Boolean, Integer, ForeignKey, Numeric, JSONB, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Prescription(Base):
    """Prescription records."""
    
    __tablename__ = "prescriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Prescription info
    prescription_number = Column(String(100))
    file_url = Column(String(500))
    file_type = Column(String(10))  # image, pdf
    
    # Doctor info
    doctor_name = Column(String(255))
    doctor_npi = Column(String(10))
    doctor_license = Column(String(50))
    doctor_phone = Column(String(20))
    doctor_address = Column(Text)
    
    # Patient info (as on prescription)
    patient_name_on_rx = Column(String(255))
    patient_dob_on_rx = Column(Date)
    
    # Dates
    issue_date = Column(Date)
    expiration_date = Column(Date)
    
    # Validation
    validation_status = Column(String(20), default="pending", index=True)  # pending, valid, invalid, needs_review, expired
    validation_confidence = Column(Numeric(3, 2))
    validation_notes = Column(Text)
    validated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    validated_at = Column(DateTime)
    
    # OCR data
    extracted_data = Column(JSONB)
    
    # Status
    status = Column(String(20), default="active", index=True)  # active, used, expired, cancelled
    usage_count = Column(Integer, default=0)
    max_uses = Column(Integer, default=1)
    
    # Relationships
    user = relationship("User", back_populates="prescriptions", foreign_keys=[user_id])
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")
    reviews = relationship("PharmacistReview", back_populates="prescription")
    
    @property
    def is_expired(self) -> bool:
        if self.expiration_date:
            return self.expiration_date < date.today()
        return False
    
    @property
    def can_be_used(self) -> bool:
        return (
            self.status == "active" and
            self.validation_status == "valid" and
            not self.is_expired and
            self.usage_count < self.max_uses
        )
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "prescription_number": self.prescription_number,
            "file_url": self.file_url,
            "file_type": self.file_type,
            "doctor_name": self.doctor_name,
            "doctor_npi": self.doctor_npi,
            "patient_name_on_rx": self.patient_name_on_rx,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "validation_status": self.validation_status,
            "validation_confidence": float(self.validation_confidence) if self.validation_confidence else None,
            "status": self.status,
            "usage_count": self.usage_count,
            "max_uses": self.max_uses,
            "can_be_used": self.can_be_used,
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PrescriptionItem(Base):
    """Individual medicines on a prescription."""
    
    __tablename__ = "prescription_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id = Column(UUID(as_uuid=True), ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    medicine_id = Column(UUID(as_uuid=True), ForeignKey("medicines.id"))
    medicine_name_on_rx = Column(String(255))
    dosage = Column(String(100))
    quantity = Column(Integer)
    quantity_unit = Column(String(20))
    frequency = Column(String(100))
    duration = Column(String(50))
    instructions = Column(Text)
    refills_allowed = Column(Integer, default=0)
    refills_remaining = Column(Integer, default=0)
    is_substitution_allowed = Column(Boolean, default=True)
    
    # Relationships
    prescription = relationship("Prescription", back_populates="items")
    medicine = relationship("Medicine")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "prescription_id": str(self.prescription_id),
            "medicine_id": str(self.medicine_id) if self.medicine_id else None,
            "medicine": self.medicine.to_dict() if self.medicine else None,
            "medicine_name_on_rx": self.medicine_name_on_rx,
            "dosage": self.dosage,
            "quantity": self.quantity,
            "quantity_unit": self.quantity_unit,
            "frequency": self.frequency,
            "duration": self.duration,
            "instructions": self.instructions,
            "refills_allowed": self.refills_allowed,
            "refills_remaining": self.refills_remaining,
            "is_substitution_allowed": self.is_substitution_allowed,
        }


class PharmacistReview(Base):
    """Pharmacist review of prescriptions."""
    
    __tablename__ = "pharmacist_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id = Column(UUID(as_uuid=True), ForeignKey("prescriptions.id"), nullable=False, index=True)
    pharmacist_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    review_status = Column(String(20), nullable=False, index=True)  # pending, approved, rejected, needs_info
    priority = Column(String(10), default="normal")  # low, normal, high, urgent
    
    reviewed_at = Column(DateTime)
    notes = Column(Text)
    rejection_reason = Column(Text)
    
    # Clinical checks
    allergy_checked = Column(Boolean, default=False)
    interaction_checked = Column(Boolean, default=False)
    contraindication_checked = Column(Boolean, default=False)
    
    # Relationships
    prescription = relationship("Prescription", back_populates="reviews")
    pharmacist = relationship("User", foreign_keys=[pharmacist_id])
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "prescription_id": str(self.prescription_id),
            "pharmacist_id": str(self.pharmacist_id),
            "review_status": self.review_status,
            "priority": self.priority,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "notes": self.notes,
            "rejection_reason": self.rejection_reason,
            "allergy_checked": self.allergy_checked,
            "interaction_checked": self.interaction_checked,
            "contraindication_checked": self.contraindication_checked,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
