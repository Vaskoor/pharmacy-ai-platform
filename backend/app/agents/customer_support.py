"""
Customer Support Agent - Handles general inquiries and FAQs.
"""
import json
from typing import Dict, Any
from datetime import datetime

from app.agents.base import BaseAgent, AgentInput, AgentOutput, AgentTool


CUSTOMER_SUPPORT_PROMPT = """You are a helpful Customer Support AI for an online pharmacy.

Your Capabilities:
1. Answer questions about medicines, shipping, returns, and policies
2. Provide general information about OTC (over-the-counter) products
3. Check order status and tracking information
4. Help with account-related questions
5. Escalate complex issues to human agents

SAFETY RULES (CRITICAL):
- NEVER provide medical advice or diagnose conditions
- NEVER recommend prescription medications
- NEVER provide specific dosages for prescription drugs
- ALWAYS suggest consulting a healthcare professional for medical questions
- ALWAYS include a disclaimer when discussing health-related topics

Response Guidelines:
- Be empathetic, clear, and concise
- Use the FAQ knowledge base for accurate information
- If unsure, acknowledge and offer to escalate
- Keep responses under 200 words when possible

For order-related questions, use the order status tool.
For medicine information, use the medicine search tool.

ALWAYS respond in JSON format:
{
    "response": "Your helpful response text",
    "confidence": 0.95,
    "escalation_needed": false,
    "suggested_actions": ["action1", "action2"],
    "disclaimer": "Medical disclaimer if applicable"
}
"""


class CustomerSupportAgent(BaseAgent):
    """Agent for handling customer support inquiries."""
    
    def __init__(self):
        tools = [
            AgentTool(
                name="search_faq",
                description="Search the FAQ knowledge base for answers",
                handler=self._search_faq,
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"}
                    },
                    "required": ["query"]
                }
            ),
            AgentTool(
                name="get_order_status",
                description="Get the status of a customer's order",
                handler=self._get_order_status,
                parameters={
                    "type": "object",
                    "properties": {
                        "order_number": {"type": "string", "description": "The order number"},
                        "user_id": {"type": "string", "description": "The user ID"}
                    },
                    "required": ["order_number"]
                }
            ),
            AgentTool(
                name="escalate_to_human",
                description="Escalate the conversation to a human agent",
                handler=self._escalate_to_human,
                parameters={
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string", "description": "Reason for escalation"},
                        "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]}
                    },
                    "required": ["reason"]
                }
            ),
            AgentTool(
                name="get_shipping_info",
                description="Get shipping information and policies",
                handler=self._get_shipping_info,
                parameters={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "enum": ["rates", "time", "policy", "international"]}
                    }
                }
            )
        ]
        
        super().__init__(
            agent_type="customer_support",
            system_prompt=CUSTOMER_SUPPORT_PROMPT,
            temperature=0.7,
            tools=tools
        )
        
        # In-memory FAQ (would be from database in production)
        self.faq_db = {
            "shipping": {
                "how long shipping": "Standard shipping takes 3-5 business days. Express shipping (1-2 days) is available for $15.99.",
                "shipping cost": "Standard shipping is $5.99 or FREE for orders over $35. Express shipping is $15.99.",
                "track order": "You can track your order in the 'Orders' section of your account or by clicking the tracking link in your shipping confirmation email."
            },
            "returns": {
                "return policy": "Unopened items can be returned within 30 days for a full refund. Prescription medications cannot be returned.",
                "how to return": "Contact our support team to initiate a return. We'll provide a prepaid shipping label."
            },
            "prescriptions": {
                "upload prescription": "You can upload your prescription in the 'Prescriptions' section. We accept JPG, PNG, and PDF files up to 10MB.",
                "prescription valid": "Prescriptions are valid for 1 year from the issue date, or as specified by your doctor.",
                "refill prescription": "You can request refills from the 'Prescriptions' section if you have remaining refills."
            },
            "general": {
                "contact support": "You can reach us via chat, email at support@pharmacy.ai, or call 1-800-PHARMACY.",
                "business hours": "Our pharmacy is open Monday-Friday 9AM-8PM, Saturday 10AM-6PM, Sunday 10AM-4PM (EST).",
                "insurance": "We accept most major insurance plans. You can add your insurance information in your profile."
            }
        }
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Process customer support request."""
        user_message = input_data.payload.get("message", "")
        
        # Build conversation context
        messages = [
            self.create_system_message(),
            {"role": "user", "content": user_message}
        ]
        
        # Call LLM with tools
        response = await self.call_llm(
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        if not response["success"]:
            return AgentOutput(
                success=False,
                error=response.get("error", "LLM call failed"),
                error_code="LLM_ERROR"
            )
        
        try:
            result = json.loads(response["content"])
            
            return AgentOutput(
                success=True,
                data={
                    "response": result.get("response", ""),
                    "confidence": result.get("confidence", 0.5),
                    "suggested_actions": result.get("suggested_actions", []),
                    "disclaimer": result.get("disclaimer")
                },
                escalation_needed=result.get("escalation_needed", False),
                confidence=result.get("confidence", 0.5)
            )
            
        except json.JSONDecodeError:
            # Return raw content if JSON parsing fails
            return AgentOutput(
                success=True,
                data={"response": response["content"]},
                confidence=0.5
            )
    
    async def _search_faq(self, query: str) -> Dict[str, Any]:
        """Search FAQ knowledge base."""
        query_lower = query.lower()
        results = []
        
        for category, items in self.faq_db.items():
            for key, value in items.items():
                if any(word in key for word in query_lower.split()):
                    results.append({
                        "category": category,
                        "question": key,
                        "answer": value
                    })
        
        return {
            "found": len(results) > 0,
            "results": results[:3]  # Return top 3
        }
    
    async def _get_order_status(self, order_number: str, user_id: str = None) -> Dict[str, Any]:
        """Get order status (would query database in production)."""
        # Mock implementation
        return {
            "order_number": order_number,
            "status": "shipped",
            "status_display": "Shipped",
            "tracking_number": "1Z999AA1234567890",
            "carrier": "UPS",
            "estimated_delivery": "2024-02-20",
            "shipped_at": "2024-02-18T10:30:00Z"
        }
    
    async def _escalate_to_human(self, reason: str, priority: str = "normal") -> Dict[str, Any]:
        """Escalate to human agent."""
        return {
            "escalated": True,
            "ticket_id": f"TKT-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "reason": reason,
            "priority": priority,
            "estimated_wait": "5-10 minutes"
        }
    
    async def _get_shipping_info(self, topic: str = "rates") -> Dict[str, Any]:
        """Get shipping information."""
        info = {
            "rates": {
                "standard": "$5.99 (FREE over $35)",
                "express": "$15.99"
            },
            "time": {
                "standard": "3-5 business days",
                "express": "1-2 business days"
            },
            "policy": "Orders placed before 2PM EST ship same day"
        }
        return info.get(topic, info)
