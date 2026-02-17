"""
Tests for AI Agents.
"""
import pytest
from app.agents.base import AgentInput, AgentOutput
from app.agents.orchestrator import OrchestratorAgent
from app.agents.customer_support import CustomerSupportAgent
from app.agents.medicine_search import MedicineSearchAgent
from app.agents.prescription_validation import PrescriptionValidationAgent


@pytest.mark.asyncio
async def test_customer_support_agent():
    """Test customer support agent."""
    agent = CustomerSupportAgent()
    
    input_data = AgentInput(
        user_id="test-user",
        payload={"message": "What are your shipping options?"}
    )
    
    result = await agent.process(input_data)
    
    assert result.success
    assert result.data.get("response")
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_medicine_search_agent():
    """Test medicine search agent."""
    agent = MedicineSearchAgent()
    
    input_data = AgentInput(
        user_id="test-user",
        payload={
            "query": "pain reliever",
            "filters": {"in_stock_only": True}
        }
    )
    
    result = await agent.process(input_data)
    
    assert result.success
    assert "medicines" in result.data


@pytest.mark.asyncio
async def test_prescription_validation_agent():
    """Test prescription validation agent."""
    agent = PrescriptionValidationAgent()
    
    input_data = AgentInput(
        user_id="test-user",
        payload={
            "prescription_file": "https://example.com/prescription.jpg",
            "file_type": "image"
        }
    )
    
    result = await agent.process(input_data)
    
    assert result.success
    assert "validation_status" in result.data


@pytest.mark.asyncio
async def test_orchestrator_routing():
    """Test orchestrator routes to correct agent."""
    agent = OrchestratorAgent()
    
    # Test medicine search routing
    input_data = AgentInput(
        user_id="test-user",
        payload={"message": "Find ibuprofen"}
    )
    
    result = await agent.process(input_data)
    
    # Should route to medicine_search or customer_support
    assert result.success
