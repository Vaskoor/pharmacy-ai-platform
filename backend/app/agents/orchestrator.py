"""
Orchestrator Agent - Central controller for all agent interactions.
"""
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.agents.base import BaseAgent, AgentInput, AgentOutput, AgentTool, agent_registry
from app.core.config import settings


ORCHESTRATOR_PROMPT = """You are the Orchestrator Agent for an AI-powered Online Pharmacy Platform.

Your role is to:
1. Analyze user requests and route them to the appropriate specialized agent
2. Coordinate multi-agent workflows for complex tasks
3. Maintain conversation context across agent boundaries
4. Aggregate responses from multiple agents
5. Handle agent failures gracefully

Available Agents:
- customer_support: General inquiries, FAQs, order status
- medicine_search: Find medicines, check availability, get details
- prescription_validation: Validate uploaded prescriptions
- pharmacist_review: Queue prescriptions for pharmacist approval
- inventory_management: Check stock, get availability
- order_processing: Create and manage orders
- payment: Process payments
- delivery: Track shipments, delivery info
- compliance_safety: Safety checks, drug interactions
- learning_feedback: Collect feedback, improve responses

Routing Rules:
- Medicine searches → medicine_search
- Prescription uploads → prescription_validation
- Order questions → customer_support (for status) or order_processing (for creation)
- Payment issues → payment
- General questions → customer_support
- Safety concerns → compliance_safety

Always respond with JSON in this format:
{
    "target_agent": "agent_type",
    "reasoning": "why this agent was chosen",
    "context_to_pass": {"key": "value"},
    "priority": "low|normal|high|urgent"
}
"""


class OrchestratorAgent(BaseAgent):
    """Central orchestrator for routing requests to specialized agents."""
    
    def __init__(self):
        super().__init__(
            agent_type="orchestrator",
            system_prompt=ORCHESTRATOR_PROMPT,
            temperature=0.3,  # Lower temperature for consistent routing
            max_tokens=500
        )
        self.agent_registry = agent_registry
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Process input and route to appropriate agent."""
        start_time = time.time()
        
        try:
            # Analyze the request to determine routing
            routing_decision = await self._analyze_and_route(input_data)
            
            target_agent_type = routing_decision.get("target_agent", "customer_support")
            context = routing_decision.get("context_to_pass", {})
            
            # Merge context into payload
            merged_payload = {**input_data.payload, **context}
            input_data.payload = merged_payload
            
            # Get target agent
            target_agent = self.agent_registry.get(target_agent_type)
            
            if not target_agent:
                return AgentOutput(
                    success=False,
                    error=f"Agent {target_agent_type} not found",
                    error_code="AGENT_NOT_FOUND",
                    data={"routing_decision": routing_decision}
                )
            
            # Execute target agent
            result = await target_agent.process(input_data)
            
            # Add routing metadata
            result.metadata["routing"] = routing_decision
            result.metadata["orchestrated_at"] = datetime.utcnow().isoformat()
            
            latency_ms = int((time.time() - start_time) * 1000)
            await self.log_action(
                input_data=input_data,
                output_data=result,
                latency_ms=latency_ms,
                tokens={"input": 0, "output": 0}
            )
            
            return result
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return AgentOutput(
                success=False,
                error=str(e),
                error_code="ORCHESTRATION_ERROR",
                metadata={"latency_ms": latency_ms}
            )
    
    async def _analyze_and_route(self, input_data: AgentInput) -> Dict[str, Any]:
        """Analyze request and determine routing."""
        user_message = input_data.payload.get("message", "")
        intent = input_data.payload.get("intent")
        
        # If intent is explicitly provided, use it
        if intent:
            routing_map = {
                "search_medicine": "medicine_search",
                "upload_prescription": "prescription_validation",
                "check_order": "customer_support",
                "create_order": "order_processing",
                "payment": "payment",
                "track_delivery": "delivery",
                "general_question": "customer_support",
                "safety_check": "compliance_safety",
            }
            return {
                "target_agent": routing_map.get(intent, "customer_support"),
                "reasoning": f"Explicit intent: {intent}",
                "context_to_pass": {},
                "priority": "normal"
            }
        
        # Use LLM for intelligent routing
        messages = [
            self.create_system_message(),
            {
                "role": "user",
                "content": f"User message: {user_message}\n\nDetermine which agent should handle this request."
            }
        ]
        
        response = await self.call_llm(
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        if response["success"]:
            import json
            try:
                return json.loads(response["content"])
            except json.JSONDecodeError:
                pass
        
        # Fallback to customer support
        return {
            "target_agent": "customer_support",
            "reasoning": "Fallback routing due to analysis failure",
            "context_to_pass": {},
            "priority": "normal"
        }
    
    async def execute_workflow(
        self,
        workflow_name: str,
        input_data: AgentInput,
        steps: List[Dict[str, Any]]
    ) -> AgentOutput:
        """Execute a multi-step workflow across multiple agents."""
        results = []
        context = input_data.payload.copy()
        
        for step in steps:
            agent_type = step["agent"]
            agent = self.agent_registry.get(agent_type)
            
            if not agent:
                return AgentOutput(
                    success=False,
                    error=f"Agent {agent_type} not found in workflow",
                    error_code="WORKFLOW_AGENT_MISSING"
                )
            
            # Update input with accumulated context
            step_input = AgentInput(
                user_id=input_data.user_id,
                conversation_id=input_data.conversation_id,
                payload={**context, **step.get("payload", {})}
            )
            
            result = await agent.process(step_input)
            results.append({"agent": agent_type, "result": result})
            
            if not result.success and not step.get("continue_on_error"):
                return AgentOutput(
                    success=False,
                    error=f"Workflow failed at step {agent_type}",
                    error_code="WORKFLOW_FAILED",
                    data={"results": results}
                )
            
            # Update context with step output
            context.update(result.data)
        
        return AgentOutput(
            success=True,
            data={
                "workflow": workflow_name,
                "results": results,
                "final_context": context
            }
        )
