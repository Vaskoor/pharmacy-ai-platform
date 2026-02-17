"""
Order and payment models.
"""
import uuid
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Text, Numeric, Integer, Date, DateTime, Boolean, ForeignKey, JSONB, INET, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Order(Base):
    """Customer orders."""
    
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Address
    shipping_address_id = Column(UUID(as_uuid=True), ForeignKey("user_addresses.id"))
    shipping_address_snapshot = Column(JSONB)
    
    # Prescription (if required)
    prescription_id = Column(UUID(as_uuid=True), ForeignKey("prescriptions.id"))
    
    # Financial
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0)
    shipping_amount = Column(Numeric(10, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    
    # Coupon
    coupon_code = Column(String(50))
    coupon_discount = Column(Numeric(10, 2))
    
    # Status
    status = Column(String(20), default="pending", index=True)  # pending, confirmed, processing, ready_for_pickup, shipped, delivered, cancelled, refunded
    payment_status = Column(String(20), default="pending", index=True)  # pending, authorized, captured, failed, refunded, partially_refunded
    
    # Delivery
    shipping_method = Column(String(50))
    tracking_number = Column(String(100))
    carrier = Column(String(50))
    estimated_delivery = Column(Date)
    shipped_at = Column(DateTime)
    delivered_at = Column(DateTime)
    
    # Notes
    customer_notes = Column(Text)
    internal_notes = Column(Text)
    
    # Metadata
    ip_address = Column(INET)
    user_agent = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order")
    prescription = relationship("Prescription")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "order_number": self.order_number,
            "user_id": str(self.user_id),
            "shipping_address": self.shipping_address_snapshot,
            "prescription_id": str(self.prescription_id) if self.prescription_id else None,
            "subtotal": float(self.subtotal),
            "tax_amount": float(self.tax_amount),
            "shipping_amount": float(self.shipping_amount),
            "discount_amount": float(self.discount_amount),
            "total_amount": float(self.total_amount),
            "currency": self.currency,
            "coupon_code": self.coupon_code,
            "status": self.status,
            "payment_status": self.payment_status,
            "shipping_method": self.shipping_method,
            "tracking_number": self.tracking_number,
            "carrier": self.carrier,
            "estimated_delivery": self.estimated_delivery.isoformat() if self.estimated_delivery else None,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "customer_notes": self.customer_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class OrderItem(Base):
    """Items within an order."""
    
    __tablename__ = "order_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    medicine_id = Column(UUID(as_uuid=True), ForeignKey("medicines.id"))
    
    # Snapshot
    medicine_name = Column(String(255), nullable=False)
    medicine_sku = Column(String(50), nullable=False)
    
    # Pricing
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    
    # Prescription item reference
    prescription_item_id = Column(UUID(as_uuid=True), ForeignKey("prescription_items.id"))
    
    # Fulfillment
    fulfilled_quantity = Column(Integer, default=0)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    medicine = relationship("Medicine")
    prescription_item = relationship("PrescriptionItem")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "order_id": str(self.order_id),
            "medicine_id": str(self.medicine_id) if self.medicine_id else None,
            "medicine_name": self.medicine_name,
            "medicine_sku": self.medicine_sku,
            "unit_price": float(self.unit_price),
            "quantity": self.quantity,
            "total_price": float(self.total_price),
            "prescription_item_id": str(self.prescription_item_id) if self.prescription_item_id else None,
            "fulfilled_quantity": self.fulfilled_quantity,
        }


class Payment(Base):
    """Payment records."""
    
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Payment details
    payment_method = Column(String(20), nullable=False)  # card, insurance, paypal, apple_pay, google_pay
    payment_provider = Column(String(50))
    provider_payment_id = Column(String(255))
    
    # Amount
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    
    # Card info (masked)
    card_last_four = Column(String(4))
    card_brand = Column(String(20))
    card_expiry_month = Column(String(2))
    card_expiry_year = Column(String(4))
    
    # Status
    status = Column(String(20), nullable=False, index=True)  # pending, authorized, captured, failed, refunded, partially_refunded, disputed
    
    # Timestamps
    authorized_at = Column(DateTime)
    captured_at = Column(DateTime)
    refunded_at = Column(DateTime)
    
    # Refund info
    refunded_amount = Column(Numeric(10, 2))
    refund_reason = Column(Text)
    
    # Fraud check
    fraud_score = Column(Numeric(3, 2))
    fraud_flags = Column(JSONB)
    
    # Response
    provider_response = Column(JSONB)
    
    # Relationships
    order = relationship("Order", back_populates="payments")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "order_id": str(self.order_id),
            "payment_method": self.payment_method,
            "amount": float(self.amount),
            "currency": self.currency,
            "card_last_four": self.card_last_four,
            "card_brand": self.card_brand,
            "status": self.status,
            "authorized_at": self.authorized_at.isoformat() if self.authorized_at else None,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
