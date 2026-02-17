"""
Conversation and chat message models.
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, ForeignKey, JSONB, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Conversation(Base):
    """Chat conversations between users and AI agents."""
    
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(100))
    
    # Metadata
    title = Column(String(255))
    conversation_type = Column(String(20), default="general")  # general, prescription, order, support
    
    # Status
    status = Column(String(20), default="active", index=True)  # active, closed, escalated
    
    # Escalation
    escalated_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    escalated_at = Column(DateTime)
    escalation_reason = Column(Text)
    
    # Satisfaction
    satisfaction_rating = Column(Integer)
    satisfaction_feedback = Column(Text)
    
    closed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="conversations", foreign_keys=[user_id])
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "session_id": self.session_id,
            "title": self.title,
            "conversation_type": self.conversation_type,
            "status": self.status,
            "satisfaction_rating": self.satisfaction_rating,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatMessage(Base):
    """Individual chat messages."""
    
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Message info
    message_type = Column(String(20), nullable=False)  # user, agent, system, pharmacist
    agent_type = Column(String(50))  # which agent sent this
    
    # Content
    content = Column(Text, nullable=False)
    content_html = Column(Text)
    
    # Structured data
    structured_data = Column(JSONB)
    
    # Media
    attachments = Column(JSONB)
    
    # Metadata
    tokens_used = Column(Integer)
    latency_ms = Column(Integer)
    
    # Feedback
    helpful = Column(Boolean)
    feedback_text = Column(Text)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "message_type": self.message_type,
            "agent_type": self.agent_type,
            "content": self.content,
            "structured_data": self.structured_data,
            "attachments": self.attachments,
            "tokens_used": self.tokens_used,
            "helpful": self.helpful,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AgentLog(Base):
    """Agent execution logs for debugging and auditing."""
    
    __tablename__ = "agent_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Agent info
    agent_type = Column(String(50), nullable=False, index=True)
    agent_instance_id = Column(String(100))
    
    # Request/Response
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    
    input_payload = Column(JSONB)
    output_payload = Column(JSONB)
    
    # Performance
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    latency_ms = Column(Integer)
    
    # Status
    status = Column(String(20), nullable=False, index=True)  # success, error, timeout, retry
    error_message = Column(Text)
    error_stack = Column(Text)
    
    # LLM specific
    model_name = Column(String(50))
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "agent_type": self.agent_type,
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "model_name": self.model_name,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuditLog(Base):
    """Compliance audit logs."""
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Who
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    user_role = Column(String(20))
    session_id = Column(String(100))
    ip_address = Column(INET)
    user_agent = Column(Text)
    
    # What
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), index=True)
    resource_id = Column(UUID(as_uuid=True))
    
    # Details
    before_state = Column(JSONB)
    after_state = Column(JSONB)
    changes_summary = Column(Text)
    
    # Compliance
    pii_involved = Column(Boolean, default=False)
    data_access_reason = Column(Text)
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "pii_involved": self.pii_involved,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
