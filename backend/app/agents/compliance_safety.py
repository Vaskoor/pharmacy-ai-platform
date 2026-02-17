"""
Compliance & Safety Agent - Ensures HIPAA compliance and safety checks.
"""
import json
import re
from typing import Dict, Any, List
from datetime import datetime
from app.agents.base import BaseAgent, AgentInput, AgentOutput, AgentTool


COMPLIANCE_SAFETY_PROMPT = """You are a Compliance & Safety AI for an online pharmacy.

Your role is to:
1. Enforce HIPAA compliance in all operations
2. Detect and flag PII (Personally Identifiable Information)
3. Audit all agent actions
4. Ensure data retention policies are followed
5. Generate compliance reports
6. Flag suspicious activities

HIPAA Rules:
- PHI (Protected Health Information) must be encrypted at rest and in transit
- Access to PHI must be logged
- Minimum necessary access principle
- Patient consent for data use
- Breach notification requirements

Safety Checks:
- Drug interaction screening
- Allergy checking
- Dosage validation
- Contraindication screening
- Duplicate therapy detection

Response Format (JSON):
{
    "compliance_check": "passed|failed|warning",
    "safety_check": "passed|failed|warning",
    "flags": ["flag1", "flag2"],
    "recommendations": ["rec1", "rec2"],
    "requires_review": false,
    "audit_log_id": "uuid"
}
"""


class ComplianceSafetyAgent(BaseAgent):
    """Agent for compliance and safety checks."""
    
    def __init__(self):
        tools = [
            AgentTool(
                name="detect_pii",
                description="Detect PII/PHI in text",
                handler=self._detect_pii,
                parameters={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"}
                    },
                    "required": ["text"]
                }
            ),
            AgentTool(
                name="anonymize_data",
                description="Anonymize PII/PHI in data",
                handler=self._anonymize_data,
                parameters={
                    "type": "object",
                    "properties": {
                        "data": {"type": "object"},
                        "fields_to_anonymize": {"type": "array"}
                    }
                }
            ),
            AgentTool(
                name="audit_log",
                description="Create audit log entry",
                handler=self._audit_log,
                parameters={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "user_id": {"type": "string"},
                        "resource_type": {"type": "string"},
                        "resource_id": {"type": "string"},
                        "pii_involved": {"type": "boolean"}
                    }
                }
            ),
            AgentTool(
                name="check_drug_safety",
                description="Check drug safety (interactions, allergies, contraindications)",
                handler=self._check_drug_safety,
                parameters={
                    "type": "object",
                    "properties": {
                        "medicine_ids": {"type": "array"},
                        "user_id": {"type": "string"}
                    }
                }
            ),
            AgentTool(
                name="validate_dosage",
                description="Validate medication dosage",
                handler=self._validate_dosage,
                parameters={
                    "type": "object",
                    "properties": {
                        "medicine_id": {"type": "string"},
                        "dosage": {"type": "string"},
                        "patient_age": {"type": "number"},
                        "patient_weight": {"type": "number"}
                    }
                }
            )
        ]
        
        super().__init__(
            agent_type="compliance_safety",
            system_prompt=COMPLIANCE_SAFETY_PROMPT,
            temperature=0.2,
            tools=tools
        )
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Process compliance/safety check request."""
        check_type = input_data.payload.get("check_type", "full")
        
        if check_type == "pii_detection":
            return await self._pii_check(input_data)
        elif check_type == "drug_safety":
            return await self._drug_safety_check(input_data)
        elif check_type == "audit":
            return await self._audit_action(input_data)
        else:
            return await self._full_compliance_check(input_data)
    
    async def _full_compliance_check(self, input_data: AgentInput) -> AgentOutput:
        """Run full compliance and safety check."""
        results = {
            "compliance_check": "passed",
            "safety_check": "passed",
            "flags": [],
            "recommendations": [],
            "requires_review": False
        }
        
        # Check for PII in payload
        payload_str = json.dumps(input_data.payload)
        pii_check = await self._detect_pii(payload_str)
        if pii_check["has_pii"]:
            results["flags"].append("pii_detected_in_payload")
            results["recommendations"].append("Ensure PII is encrypted")
        
        # Drug safety check if medicines involved
        if "medicine_ids" in input_data.payload:
            safety = await self._check_drug_safety(
                input_data.payload["medicine_ids"],
                input_data.user_id
            )
            if safety.get("has_issues"):
                results["safety_check"] = "warning"
                results["flags"].extend(safety.get("issues", []))
                results["requires_review"] = True
        
        # Create audit log
        audit = await self._audit_log(
            action="compliance_check",
            user_id=input_data.user_id,
            resource_type="compliance",
            pii_involved=pii_check["has_pii"]
        )
        results["audit_log_id"] = audit.get("log_id")
        
        return AgentOutput(
            success=True,
            data=results,
            confidence=0.95
        )
    
    async def _pii_check(self, input_data: AgentInput) -> AgentOutput:
        """Check for PII in text."""
        text = input_data.payload.get("text", "")
        result = await self._detect_pii(text)
        
        return AgentOutput(
            success=True,
            data=result,
            confidence=0.9
        )
    
    async def _drug_safety_check(self, input_data: AgentInput) -> AgentOutput:
        """Check drug safety."""
        medicine_ids = input_data.payload.get("medicine_ids", [])
        user_id = input_data.user_id
        
        result = await self._check_drug_safety(medicine_ids, user_id)
        
        return AgentOutput(
            success=True,
            data=result,
            escalation_needed=result.get("has_issues", False)
        )
    
    async def _audit_action(self, input_data: AgentInput) -> AgentOutput:
        """Create audit log entry."""
        audit = await self._audit_log(
            action=input_data.payload.get("action", "unknown"),
            user_id=input_data.user_id,
            resource_type=input_data.payload.get("resource_type"),
            resource_id=input_data.payload.get("resource_id"),
            pii_involved=input_data.payload.get("pii_involved", False)
        )
        
        return AgentOutput(
            success=True,
            data=audit
        )
    
    async def _detect_pii(self, text: str) -> Dict[str, Any]:
        """Detect PII/PHI in text."""
        pii_patterns = {
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            "dob": r'\b(0[1-9]|1[0-2])[/-](0[1-9]|[12]\d|3[01])[/-](19|20)\d{2}\b',
            "mrn": r'\bMRN[\s:]?\d{6,10}\b',
        }
        
        detected = {}
        for pii_type, pattern in pii_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                detected[pii_type] = len(matches)
        
        return {
            "has_pii": len(detected) > 0,
            "detected_types": list(detected.keys()),
            "count": sum(detected.values()),
            "recommendation": "Anonymize or encrypt" if detected else "No PII detected"
        }
    
    async def _anonymize_data(
        self,
        data: Dict,
        fields_to_anonymize: List[str] = None
    ) -> Dict[str, Any]:
        """Anonymize PII in data."""
        import hashlib
        
        fields = fields_to_anonymize or ["name", "email", "phone", "address", "ssn"]
        anonymized = data.copy()
        
        for field in fields:
            if field in anonymized:
                value = str(anonymized[field])
                anonymized[field] = hashlib.sha256(value.encode()).hexdigest()[:16]
        
        return {
            "anonymized": True,
            "data": anonymized,
            "fields_anonymized": fields
        }
    
    async def _audit_log(
        self,
        action: str,
        user_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        pii_involved: bool = False
    ) -> Dict[str, Any]:
        """Create audit log entry."""
        log_id = f"audit-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        return {
            "log_id": log_id,
            "logged": True,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "pii_involved": pii_involved
        }
    
    async def _check_drug_safety(
        self,
        medicine_ids: List[str],
        user_id: str = None
    ) -> Dict[str, Any]:
        """Check drug safety (interactions, allergies)."""
        issues = []
        
        # Mock interaction check
        if len(medicine_ids) > 1:
            issues.append("Multiple medications - check interactions")
        
        # Mock allergy check
        if user_id:
            # Would check user's allergy profile
            pass
        
        return {
            "has_issues": len(issues) > 0,
            "issues": issues,
            "recommendations": ["Consult pharmacist"] if issues else []
        }
    
    async def _validate_dosage(
        self,
        medicine_id: str,
        dosage: str,
        patient_age: float = None,
        patient_weight: float = None
    ) -> Dict[str, Any]:
        """Validate medication dosage."""
        # Mock dosage validation
        return {
            "valid": True,
            "warnings": [],
            "recommended_range": "As prescribed by doctor"
        }
