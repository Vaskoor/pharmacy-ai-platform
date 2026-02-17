"""
Medicine Search Agent - Semantic search and medicine recommendations.
"""
import json
from typing import Dict, Any, List
from datetime import datetime

from app.agents.base import BaseAgent, AgentInput, AgentOutput, AgentTool


MEDICINE_SEARCH_PROMPT = """You are a Medicine Search AI for an online pharmacy.

Your Capabilities:
1. Search for medicines by name, generic name, symptoms, or category
2. Provide detailed medicine information
3. Check availability and pricing
4. Recommend OTC alternatives
5. Check for drug interactions

SAFETY RULES (CRITICAL):
- NEVER provide medical advice or treatment recommendations
- NEVER diagnose conditions
- ALWAYS include: "Consult a healthcare professional before use"
- For prescription drugs, remind users a valid prescription is required
- Flag potential drug interactions clearly

Response Guidelines:
- Be accurate and specific about medicine details
- Include active ingredients
- Mention if prescription is required
- Highlight important warnings
- Suggest alternatives when appropriate

ALWAYS respond in JSON format:
{
    "medicines": [
        {
            "name": "Medicine Name",
            "generic_name": "Generic Name",
            "description": "Brief description",
            "price": 29.99,
            "in_stock": true,
            "prescription_required": false,
            "warnings": ["warning1", "warning2"],
            "confidence_score": 0.95
        }
    ],
    "total_count": 5,
    "suggestions": ["related search 1", "related search 2"],
    "disclaimer": "Medical disclaimer"
}
"""


class MedicineSearchAgent(BaseAgent):
    """Agent for searching and recommending medicines."""
    
    def __init__(self):
        tools = [
            AgentTool(
                name="semantic_search",
                description="Search medicines by semantic similarity",
                handler=self._semantic_search,
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "category": {"type": "string"},
                        "in_stock_only": {"type": "boolean"},
                        "otc_only": {"type": "boolean"},
                        "limit": {"type": "integer", "default": 10}
                    },
                    "required": ["query"]
                }
            ),
            AgentTool(
                name="get_medicine_details",
                description="Get detailed information about a medicine",
                handler=self._get_medicine_details,
                parameters={
                    "type": "object",
                    "properties": {
                        "medicine_id": {"type": "string"},
                        "sku": {"type": "string"}
                    }
                }
            ),
            AgentTool(
                name="check_interactions",
                description="Check for drug interactions",
                handler=self._check_interactions,
                parameters={
                    "type": "object",
                    "properties": {
                        "medicine_ids": {"type": "array", "items": {"type": "string"}},
                        "user_id": {"type": "string"}
                    },
                    "required": ["medicine_ids"]
                }
            ),
            AgentTool(
                name="get_alternatives",
                description="Get alternative medicines",
                handler=self._get_alternatives,
                parameters={
                    "type": "object",
                    "properties": {
                        "medicine_id": {"type": "string"},
                        "same_generic": {"type": "boolean", "default": True}
                    },
                    "required": ["medicine_id"]
                }
            ),
            AgentTool(
                name="check_allergies",
                description="Check medicine against user allergies",
                handler=self._check_allergies,
                parameters={
                    "type": "object",
                    "properties": {
                        "medicine_id": {"type": "string"},
                        "user_id": {"type": "string"}
                    },
                    "required": ["medicine_id", "user_id"]
                }
            )
        ]
        
        super().__init__(
            agent_type="medicine_search",
            system_prompt=MEDICINE_SEARCH_PROMPT,
            temperature=0.5,
            tools=tools
        )
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Process medicine search request."""
        query = input_data.payload.get("query", "")
        filters = input_data.payload.get("filters", {})
        user_id = input_data.user_id
        
        # Perform semantic search
        search_results = await self._semantic_search(
            query=query,
            category=filters.get("category"),
            in_stock_only=filters.get("in_stock_only", True),
            otc_only=filters.get("otc_only", False),
            limit=filters.get("limit", 10)
        )
        
        if not search_results["found"]:
            return AgentOutput(
                success=True,
                data={
                    "medicines": [],
                    "total_count": 0,
                    "suggestions": ["Try a different search term", "Browse by category"],
                    "disclaimer": "Consult a healthcare professional before using any medication."
                }
            )
        
        # Check interactions if user has current medications
        medicines = search_results["results"]
        if user_id and len(medicines) > 0:
            medicine_ids = [m["id"] for m in medicines[:3]]
            interactions = await self._check_interactions(medicine_ids, user_id)
            
            # Add interaction warnings
            for med in medicines:
                med["interaction_warning"] = interactions.get("warnings", {}).get(med["id"])
        
        # Build LLM response
        messages = [
            self.create_system_message(),
            {
                "role": "user",
                "content": f"Search query: {query}\n\nResults: {json.dumps(medicines[:5])}\n\nFormat the response."
            }
        ]
        
        response = await self.call_llm(
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        if response["success"]:
            try:
                result = json.loads(response["content"])
                return AgentOutput(
                    success=True,
                    data=result,
                    confidence=0.9
                )
            except json.JSONDecodeError:
                pass
        
        # Return raw search results
        return AgentOutput(
            success=True,
            data={
                "medicines": medicines[:10],
                "total_count": search_results["total"],
                "suggestions": [],
                "disclaimer": "Consult a healthcare professional before using any medication."
            }
        )
    
    async def _semantic_search(
        self,
        query: str,
        category: str = None,
        in_stock_only: bool = True,
        otc_only: bool = False,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Perform semantic search for medicines."""
        # This would use vector DB in production
        # Mock implementation with sample data
        
        sample_medicines = [
            {
                "id": "med-001",
                "name": "Advil Pain Reliever",
                "generic_name": "Ibuprofen",
                "description": "Pain reliever and fever reducer",
                "price": 12.99,
                "in_stock": True,
                "prescription_required": False,
                "category": "Pain Relief",
                "active_ingredient": "Ibuprofen 200mg",
                "warnings": ["May cause stomach upset", "Avoid if allergic to NSAIDs"]
            },
            {
                "id": "med-002",
                "name": "Tylenol Extra Strength",
                "generic_name": "Acetaminophen",
                "description": "Fast pain relief",
                "price": 9.99,
                "in_stock": True,
                "prescription_required": False,
                "category": "Pain Relief",
                "active_ingredient": "Acetaminophen 500mg",
                "warnings": ["Do not exceed 3000mg per day", "Avoid alcohol"]
            },
            {
                "id": "med-003",
                "name": "Claritin Allergy Relief",
                "generic_name": "Loratadine",
                "description": "24-hour allergy relief",
                "price": 19.99,
                "in_stock": True,
                "prescription_required": False,
                "category": "Allergy",
                "active_ingredient": "Loratadine 10mg",
                "warnings": ["May cause drowsiness in some people"]
            },
            {
                "id": "med-004",
                "name": "Zyrtec Allergy Tablets",
                "generic_name": "Cetirizine",
                "description": "Allergy symptom relief",
                "price": 21.99,
                "in_stock": True,
                "prescription_required": False,
                "category": "Allergy",
                "active_ingredient": "Cetirizine 10mg",
                "warnings": ["May cause drowsiness"]
            },
            {
                "id": "med-005",
                "name": "Amoxicillin 500mg",
                "generic_name": "Amoxicillin",
                "description": "Antibiotic for bacterial infections",
                "price": 15.99,
                "in_stock": True,
                "prescription_required": True,
                "category": "Prescription Medications",
                "active_ingredient": "Amoxicillin 500mg",
                "warnings": ["Complete full course", "May cause diarrhea"]
            }
        ]
        
        # Simple keyword matching (would be vector search in production)
        query_lower = query.lower()
        results = []
        
        for med in sample_medicines:
            score = 0
            if query_lower in med["name"].lower():
                score += 10
            if query_lower in med["generic_name"].lower():
                score += 8
            if query_lower in med["category"].lower():
                score += 5
            if query_lower in med["description"].lower():
                score += 3
            
            if category and med["category"] == category:
                score += 5
            
            if in_stock_only and not med["in_stock"]:
                continue
            
            if otc_only and med["prescription_required"]:
                continue
            
            if score > 0:
                med["confidence_score"] = min(score / 20, 1.0)
                results.append(med)
        
        # Sort by confidence
        results.sort(key=lambda x: x["confidence_score"], reverse=True)
        
        return {
            "found": len(results) > 0,
            "results": results[:limit],
            "total": len(results)
        }
    
    async def _get_medicine_details(self, medicine_id: str = None, sku: str = None) -> Dict[str, Any]:
        """Get detailed medicine information."""
        # Mock implementation
        return {
            "id": medicine_id or "med-001",
            "sku": sku or "SKU001",
            "name": "Advil Pain Reliever",
            "full_description": "Advil provides fast pain relief for headaches, muscle aches, and fever.",
            "dosage_instructions": "Take 1-2 tablets every 4-6 hours as needed",
            "side_effects": ["Stomach upset", "Heartburn", "Dizziness"],
            "contraindications": ["Pregnancy (3rd trimester)", "Stomach ulcers", "Kidney disease"],
            "storage": "Store at room temperature away from moisture"
        }
    
    async def _check_interactions(self, medicine_ids: List[str], user_id: str = None) -> Dict[str, Any]:
        """Check for drug interactions."""
        # Mock implementation
        warnings = {}
        has_interactions = False
        
        # Simulate interaction between certain medicines
        if "med-001" in medicine_ids and "med-002" in medicine_ids:
            warnings["med-001"] = "Taking with other NSAIDs may increase stomach bleeding risk"
            has_interactions = True
        
        return {
            "has_interactions": has_interactions,
            "warnings": warnings,
            "recommendation": "Consult your pharmacist" if has_interactions else "No known interactions"
        }
    
    async def _get_alternatives(self, medicine_id: str, same_generic: bool = True) -> Dict[str, Any]:
        """Get alternative medicines."""
        # Mock implementation
        return {
            "alternatives": [
                {
                    "id": "alt-001",
                    "name": "Generic Ibuprofen",
                    "price": 7.99,
                    "savings": 5.00
                }
            ]
        }
    
    async def _check_allergies(self, medicine_id: str, user_id: str) -> Dict[str, Any]:
        """Check medicine against user allergies."""
        # Mock implementation
        return {
            "safe": True,
            "allergen_found": None,
            "warning": None
        }
