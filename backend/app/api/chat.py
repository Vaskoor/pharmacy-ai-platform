"""
Chat API routes for AI agent conversations.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime

from app.agents.base import AgentInput, AgentOutput
from app.agents import orchestrator, agent_registry
from app.api.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat"])


# Pydantic models
class ChatMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context: Optional[dict] = Field(default_factory=dict)


class ChatMessageResponse(BaseModel):
    id: str
    conversation_id: str
    message: str
    response: str
    agent_type: str
    confidence: float
    structured_data: Optional[dict] = None
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str
    title: Optional[str]
    conversation_type: str
    status: str
    created_at: datetime
    updated_at: datetime


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)


manager = ConnectionManager()


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a message to the AI and get a response."""
    
    # Create agent input
    agent_input = AgentInput(
        user_id=current_user["id"],
        conversation_id=request.conversation_id,
        payload={
            "message": request.message,
            **request.context
        }
    )
    
    # Process through orchestrator
    result: AgentOutput = await orchestrator.process(agent_input)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error or "Failed to process message"
        )
    
    # Generate response
    response_id = f"msg-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    conversation_id = request.conversation_id or f"conv-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    return ChatMessageResponse(
        id=response_id,
        conversation_id=conversation_id,
        message=request.message,
        response=result.data.get("response", ""),
        agent_type=result.metadata.get("routing", {}).get("target_agent", "unknown"),
        confidence=result.confidence,
        structured_data=result.data,
        created_at=datetime.utcnow()
    )


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0
):
    """Get user's conversation history."""
    # In production: query from database
    return [
        ConversationResponse(
            id=f"conv-{i}",
            title=f"Conversation {i}",
            conversation_type="general",
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        for i in range(limit)
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    limit: int = 50
):
    """Get messages in a conversation."""
    # In production: query from database
    return []


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a conversation."""
    # In production: soft delete from database
    return {"message": "Conversation deleted"}


@router.post("/conversations/{conversation_id}/feedback")
async def submit_feedback(
    conversation_id: str,
    rating: int,
    feedback: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Submit feedback for a conversation."""
    # In production: save to database
    return {"message": "Feedback submitted", "rating": rating}


# WebSocket endpoint for real-time chat
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket for real-time chat."""
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            message = data.get("message", "")
            conversation_id = data.get("conversation_id")
            
            # Create agent input
            agent_input = AgentInput(
                user_id=user_id,
                conversation_id=conversation_id,
                payload={"message": message, **data.get("context", {})}
            )
            
            # Process through orchestrator
            result: AgentOutput = await orchestrator.process(agent_input)
            
            # Send response back
            response = {
                "type": "agent_response",
                "conversation_id": conversation_id,
                "response": result.data.get("response", ""),
                "agent_type": result.metadata.get("routing", {}).get("target_agent", "unknown"),
                "confidence": result.confidence,
                "structured_data": result.data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await manager.send_message(user_id, response)
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        await manager.send_message(user_id, {
            "type": "error",
            "error": str(e)
        })
        manager.disconnect(user_id)


@router.get("/agents")
async def list_agents(current_user: dict = Depends(get_current_user)):
    """List available agents."""
    return {
        "agents": agent_registry.list_agents()
    }
