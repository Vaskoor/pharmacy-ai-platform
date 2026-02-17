"""
Prescription Validation Agent - Validates prescription images and PDFs.
"""
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from app.agents.base import BaseAgent, AgentInput, AgentOutput, AgentTool


PRESCRIPTION_VALIDATION_PROMPT = """You are a Prescription Validation AI for an online pharmacy.

Your role is to:
1. Extract information from prescription images/PDFs using OCR
2. Validate prescription format and required fields
3. Check for tampering or fraud indicators
4. Verify prescription hasn't expired
5. Flag controlled substances

Required Fields on a Valid Prescription:
- Patient name
- Doctor name and credentials
- Doctor NPI (National Provider Identifier) or license
- Medication name and dosage
- Quantity prescribed
- Instructions (sig)
- Issue date
- Doctor signature

Validation Rules:
- Prescription must be dated within last 30 days (or have valid dates)
- All required fields must be present
- Controlled substances require additional verification
- Digital prescriptions must have valid electronic signatures

Response Format (JSON):
{
    "validation_status": "valid|invalid|needs_review",
    "confidence": 0.95,
    "extracted_data": {
        "patient_name": "",
        "doctor_name": "",
        "doctor_npi": "",
        "medicines": [{"name": "", "dosage": "", "quantity": 0}],
        "issue_date": "",
        "expiration_date": ""
    },
    "flags": ["flag1", "flag2"],
    "error_message": null,
    "requires_pharmacist_review": false
}
"""


class PrescriptionValidationAgent(BaseAgent):
    """Agent for validating prescription documents."""
    
    def __init__(self):
        tools = [
            AgentTool(
                name="extract_text_ocr",
                description="Extract text from prescription image/PDF using OCR",
                handler=self._extract_text_ocr,
                parameters={
                    "type": "object",
                    "properties": {
                        "file_url": {"type": "string"},
                        "file_type": {"type": "string", "enum": ["image", "pdf"]}
                    },
                    "required": ["file_url"]
                }
            ),
            AgentTool(
                name="validate_doctor_npi",
                description="Validate doctor's NPI number",
                handler=self._validate_doctor_npi,
                parameters={
                    "type": "object",
                    "properties": {
                        "npi": {"type": "string"}
                    },
                    "required": ["npi"]
                }
            ),
            AgentTool(
                name="check_controlled_substance",
                description="Check if medicine is a controlled substance",
                handler=self._check_controlled_substance,
                parameters={
                    "type": "object",
                    "properties": {
                        "medicine_name": {"type": "string"}
                    },
                    "required": ["medicine_name"]
                }
            ),
            AgentTool(
                name="queue_for_review",
                description="Queue prescription for pharmacist review",
                handler=self._queue_for_review,
                parameters={
                    "type": "object",
                    "properties": {
                        "prescription_id": {"type": "string"},
                        "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]}
                    },
                    "required": ["prescription_id"]
                }
            )
        ]
        
        super().__init__(
            agent_type="prescription_validation",
            system_prompt=PRESCRIPTION_VALIDATION_PROMPT,
            temperature=0.3,
            tools=tools
        )
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Process prescription validation request."""
        file_url = input_data.payload.get("prescription_file")
        file_type = input_data.payload.get("file_type", "image")
        user_id = input_data.user_id
        
        if not file_url:
            return AgentOutput(
                success=False,
                error="No prescription file provided",
                error_code="MISSING_FILE"
            )
        
        # Step 1: Extract text via OCR
        ocr_result = await self._extract_text_ocr(file_url, file_type)
        
        if not ocr_result["success"]:
            return AgentOutput(
                success=False,
                error="Failed to extract text from prescription",
                error_code="OCR_ERROR",
                data={"ocr_error": ocr_result.get("error")}
            )
        
        extracted_text = ocr_result["text"]
        
        # Step 2: Use LLM to parse and validate
        messages = [
            self.create_system_message(),
            {
                "role": "user",
                "content": f"Extracted text from prescription:\n\n{extracted_text}\n\nParse and validate this prescription."
            }
        ]
        
        response = await self.call_llm(
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        if not response["success"]:
            return AgentOutput(
                success=False,
                error="Failed to parse prescription",
                error_code="PARSING_ERROR"
            )
        
        try:
            validation_result = json.loads(response["content"])
        except json.JSONDecodeError:
            return AgentOutput(
                success=False,
                error="Invalid validation response format",
                error_code="INVALID_RESPONSE"
            )
        
        # Step 3: Additional validations
        flags = validation_result.get("flags", [])
        extracted_data = validation_result.get("extracted_data", {})
        
        # Check expiration
        issue_date_str = extracted_data.get("issue_date")
        if issue_date_str:
            try:
                issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d").date()
                days_old = (date.today() - issue_date).days
                
                if days_old > 180:  # 6 months
                    flags.append("prescription_over_6_months_old")
                    validation_result["validation_status"] = "invalid"
                elif days_old > 30:
                    flags.append("prescription_over_30_days_old")
            except ValueError:
                flags.append("invalid_issue_date")
        
        # Check for controlled substances
        medicines = extracted_data.get("medicines", [])
        controlled_substances = []
        for med in medicines:
            cs_check = await self._check_controlled_substance(med.get("name", ""))
            if cs_check.get("is_controlled"):
                controlled_substances.append(med["name"])
                flags.append(f"controlled_substance_{cs_check.get('schedule', 'unknown')}")
        
        # Determine if pharmacist review is needed
        needs_review = (
            validation_result.get("validation_status") == "needs_review" or
            len(controlled_substances) > 0 or
            validation_result.get("confidence", 1.0) < 0.8 or
            "suspicious_format" in flags
        )
        
        validation_result["flags"] = flags
        validation_result["requires_pharmacist_review"] = needs_review
        validation_result["controlled_substances_found"] = controlled_substances
        
        return AgentOutput(
            success=True,
            data=validation_result,
            confidence=validation_result.get("confidence", 0.5),
            escalation_needed=needs_review
        )
    
    async def _extract_text_ocr(self, file_url: str, file_type: str) -> Dict[str, Any]:
        """Extract text from prescription using OCR."""
        # Mock implementation - would use AWS Textract or similar in production
        
        # Simulate different prescription formats
        sample_prescriptions = [
            """
            DR. JOHN SMITH, MD
            NPI: 1234567890
            License: MD12345
            
            PATIENT: Jane Doe
            DOB: 01/15/1985
            
            Rx: Amoxicillin 500mg
            Sig: Take 1 capsule three times daily for 7 days
            Qty: 21
            Refills: 0
            
            Date: 2024-02-15
            
            [SIGNATURE]
            """,
            """
            CITY MEDICAL CENTER
            Dr. Sarah Johnson
            NPI: 0987654321
            
            Patient: Robert Brown
            Date: 2024-02-10
            
            Medication: Lisinopril 10mg
            Directions: Take once daily
            Quantity: 30
            Refills: 3
            
            Dr. Sarah Johnson
            """
        ]
        
        import random
        selected = random.choice(sample_prescriptions)
        
        return {
            "success": True,
            "text": selected.strip(),
            "confidence": 0.92
        }
    
    async def _validate_doctor_npi(self, npi: str) -> Dict[str, Any]:
        """Validate doctor's NPI number."""
        # Mock implementation - would call NPPES API in production
        
        # NPI should be 10 digits
        if not re.match(r'^\d{10}$', npi):
            return {
                "valid": False,
                "error": "NPI must be 10 digits"
            }
        
        # Check Luhn algorithm (simplified)
        return {
            "valid": True,
            "doctor_name": "Dr. John Smith",
            "specialty": "Internal Medicine",
            "state": "CA",
            "verified": True
        }
    
    async def _check_controlled_substance(self, medicine_name: str) -> Dict[str, Any]:
        """Check if medicine is a controlled substance."""
        # Mock implementation
        controlled_meds = {
            "adderall": {"schedule": "II", "is_controlled": True},
            "oxycontin": {"schedule": "II", "is_controlled": True},
            "xanax": {"schedule": "IV", "is_controlled": True},
            "valium": {"schedule": "IV", "is_controlled": True},
            "tramadol": {"schedule": "IV", "is_controlled": True},
            "codeine": {"schedule": "II", "is_controlled": True},
        }
        
        med_lower = medicine_name.lower()
        for name, info in controlled_meds.items():
            if name in med_lower:
                return {
                    "is_controlled": True,
                    "schedule": info["schedule"],
                    "additional_requirements": ["Pharmacist verification required"]
                }
        
        return {
            "is_controlled": False,
            "schedule": None
        }
    
    async def _queue_for_review(
        self,
        prescription_id: str,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Queue prescription for pharmacist review."""
        return {
            "queued": True,
            "review_id": f"REV-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "priority": priority,
            "estimated_review_time": "15-30 minutes",
            "notification_method": "email"
        }
