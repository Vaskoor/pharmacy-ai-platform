"""
Inventory management models.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Date, DateTime, ForeignKey, Numeric, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Inventory(Base):
    """Current inventory levels for medicines."""
    
    __tablename__ = "inventory"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medicine_id = Column(UUID(as_uuid=True), ForeignKey("medicines.id"), nullable=False, unique=True)
    quantity_available = Column(Integer, nullable=False, default=0)
    quantity_reserved = Column(Integer, nullable=False, default=0)
    quantity_on_order = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, default=10)
    reorder_quantity = Column(Integer, default=50)
    warehouse_location = Column(String(50))
    batch_number = Column(String(50))
    expiry_date = Column(Date)
    last_counted_at = Column(DateTime)
    
    # Relationships
    medicine = relationship("Medicine", back_populates="inventory")
    transactions = relationship("InventoryTransaction", back_populates="inventory")
    
    @property
    def quantity_on_hand(self) -> int:
        """Calculate actual available quantity."""
        return self.quantity_available - self.quantity_reserved
    
    @property
    def is_low_stock(self) -> bool:
        """Check if inventory is below reorder level."""
        return self.quantity_available <= self.reorder_level
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "medicine_id": str(self.medicine_id),
            "quantity_available": self.quantity_available,
            "quantity_reserved": self.quantity_reserved,
            "quantity_on_hand": self.quantity_on_hand,
            "quantity_on_order": self.quantity_on_order,
            "reorder_level": self.reorder_level,
            "warehouse_location": self.warehouse_location,
            "batch_number": self.batch_number,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "is_low_stock": self.is_low_stock,
        }


class InventoryTransaction(Base):
    """Audit trail for inventory changes."""
    
    __tablename__ = "inventory_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id = Column(UUID(as_uuid=True), ForeignKey("inventory.id"), nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False, index=True)  # in, out, adjustment, return, expired
    quantity = Column(Integer, nullable=False)
    previous_quantity = Column(Integer, nullable=False)
    new_quantity = Column(Integer, nullable=False)
    reference_type = Column(String(50))  # order, prescription, manual
    reference_id = Column(UUID(as_uuid=True))
    notes = Column(Text)
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    inventory = relationship("Inventory", back_populates="transactions")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "inventory_id": str(self.inventory_id),
            "transaction_type": self.transaction_type,
            "quantity": self.quantity,
            "previous_quantity": self.previous_quantity,
            "new_quantity": self.new_quantity,
            "reference_type": self.reference_type,
            "reference_id": str(self.reference_id) if self.reference_id else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
