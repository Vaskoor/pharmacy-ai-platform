"""
AI Agents for the Pharmacy Platform.
"""
from app.agents.base import BaseAgent, AgentInput, AgentOutput, AgentTool, AgentRegistry, agent_registry
from app.agents.orchestrator import OrchestratorAgent
from app.agents.customer_support import CustomerSupportAgent
from app.agents.medicine_search import MedicineSearchAgent
from app.agents.prescription_validation import PrescriptionValidationAgent
from app.agents.order_processing import OrderProcessingAgent
from app.agents.compliance_safety import ComplianceSafetyAgent

# Agent instances
orchestrator = OrchestratorAgent()
customer_support = CustomerSupportAgent()
medicine_search = MedicineSearchAgent()
prescription_validation = PrescriptionValidationAgent()
order_processing = OrderProcessingAgent()
compliance_safety = ComplianceSafetyAgent()

# Register all agents
def register_agents():
    """Register all agents with the registry."""
    agent_registry.register("orchestrator", orchestrator)
    agent_registry.register("customer_support", customer_support)
    agent_registry.register("medicine_search", medicine_search)
    agent_registry.register("prescription_validation", prescription_validation)
    agent_registry.register("order_processing", order_processing)
    agent_registry.register("compliance_safety", compliance_safety)


__all__ = [
    "BaseAgent",
    "AgentInput",
    "AgentOutput",
    "AgentTool",
    "AgentRegistry",
    "agent_registry",
    "OrchestratorAgent",
    "CustomerSupportAgent",
    "MedicineSearchAgent",
    "PrescriptionValidationAgent",
    "OrderProcessingAgent",
    "ComplianceSafetyAgent",
    "orchestrator",
    "customer_support",
    "medicine_search",
    "prescription_validation",
    "order_processing",
    "compliance_safety",
    "register_agents",
]
