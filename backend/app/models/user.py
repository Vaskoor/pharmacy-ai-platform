"""
User models for authentication and profile management.
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Boolean, DateTime, Date, Text, ARRAY, ForeignKey, Integer, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    """User model for customers, pharmacists, and admins."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    date_of_birth = Column(Date)
    role = Column(String(20), nullable=False, default="customer")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime)
    phone_verified_at = Column(DateTime)
    last_login_at = Column(DateTime)
    deleted_at = Column(DateTime)
    
    # Relationships
    addresses = relationship("UserAddress", back_populates="user", cascade="all, delete-orphan")
    health_profile = relationship("UserHealthProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="user")
    orders = relationship("Order", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "role": self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserAddress(Base):
    """User addresses for shipping."""
    
    __tablename__ = "user_addresses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    address_type = Column(String(20), default="home")
    street_address = Column(Text, nullable=False)
    apartment = Column(String(50))
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), default="USA")
    is_default = Column(Boolean, default=False)
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    
    # Relationships
    user = relationship("User", back_populates="addresses")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "address_type": self.address_type,
            "street_address": self.street_address,
            "apartment": self.apartment,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "is_default": self.is_default,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
        }


class UserHealthProfile(Base):
    """User health information including allergies and conditions."""
    
    __tablename__ = "user_health_profile"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    allergies = Column(ARRAY(String))
    medical_conditions = Column(ARRAY(String))
    current_medications = Column(ARRAY(String))
    emergency_contact_name = Column(String(100))
    emergency_contact_phone = Column(String(20))
    blood_type = Column(String(5))
    notes = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="health_profile")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "allergies": self.allergies or [],
            "medical_conditions": self.medical_conditions or [],
            "current_medications": self.current_medications or [],
            "emergency_contact_name": self.emergency_contact_name,
            "emergency_contact_phone": self.emergency_contact_phone,
            "blood_type": self.blood_type,
            "notes": self.notes,
        }
