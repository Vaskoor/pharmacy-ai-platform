"""
Prescription API routes.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, date

from app.agents.base import AgentInput
from app.agents import prescription_validation
from app.api.auth import get_current_user

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


# Pydantic models
class PrescriptionItem(BaseModel):
    medicine_name: str
    dosage: Optional[str]
    quantity: Optional[int]
    instructions: Optional[str]


class PrescriptionResponse(BaseModel):
    id: str
    prescription_number: Optional[str]
    file_url: Optional[str]
    doctor_name: Optional[str]
    doctor_npi: Optional[str]
    patient_name_on_rx: Optional[str]
    issue_date: Optional[date]
    expiration_date: Optional[date]
    validation_status: str
    status: str
    usage_count: int
    max_uses: int
    can_be_used: bool
    created_at: datetime


class PrescriptionUploadResponse(BaseModel):
    id: str
    validation_status: str
    confidence: float
    extracted_data: dict
    flags: List[str]
    requires_pharmacist_review: bool
    message: str


class PrescriptionValidationResult(BaseModel):
    validation_status: str
    confidence: float
    extracted_data: dict
    flags: List[str]
    error_message: Optional[str]
    requires_pharmacist_review: bool


# Sample data
SAMPLE_PRESCRIPTIONS = []


@router.get("", response_model=List[PrescriptionResponse])
async def list_prescriptions(
    status: Optional[str] = Query(None, enum=["active", "used", "expired", "cancelled"]),
    validation_status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """List user's prescriptions."""
    # In production: query from database
    return [
        PrescriptionResponse(
            id="rx-001",
            prescription_number="RX123456",
            file_url="https://example.com/prescription1.jpg",
            doctor_name="Dr. John Smith",
            doctor_npi="1234567890",
            patient_name_on_rx="Jane Doe",
            issue_date=date(2024, 2, 1),
            expiration_date=date(2024, 8, 1),
            validation_status="valid",
            status="active",
            usage_count=0,
            max_uses=1,
            can_be_used=True,
            created_at=datetime.utcnow()
        )
    ]


@router.post("/upload", response_model=PrescriptionUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_prescription(
    file: UploadFile = File(..., description="Prescription image or PDF"),
    current_user: dict = Depends(get_current_user)
):
    """Upload and validate a prescription."""
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # In production: upload to S3, then process
    file_url = f"https://s3.example.com/prescriptions/{current_user['id']}/{file.filename}"
    file_type = "pdf" if file.content_type == "application/pdf" else "image"
    
    # Process through prescription validation agent
    agent_input = AgentInput(
        user_id=current_user["id"],
        payload={
            "prescription_file": file_url,
            "file_type": file_type
        }
    )
    
    result = await prescription_validation.process(agent_input)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error or "Failed to validate prescription"
        )
    
    # Generate prescription ID
    prescription_id = f"rx-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    
    return PrescriptionUploadResponse(
        id=prescription_id,
        validation_status=result.data.get("validation_status", "needs_review"),
        confidence=result.data.get("confidence", 0.5),
        extracted_data=result.data.get("extracted_data", {}),
        flags=result.data.get("flags", []),
        requires_pharmacist_review=result.data.get("requires_pharmacist_review", True),
        message="Prescription uploaded successfully. A pharmacist will review it shortly."
    )


@router.get("/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get prescription details."""
    # In production: query from database
    if prescription_id != "rx-001":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found"
        )
    
    return PrescriptionResponse(
        id=prescription_id,
        prescription_number="RX123456",
        file_url="https://example.com/prescription1.jpg",
        doctor_name="Dr. John Smith",
        doctor_npi="1234567890",
        patient_name_on_rx="Jane Doe",
        issue_date=date(2024, 2, 1),
        expiration_date=date(2024, 8, 1),
        validation_status="valid",
        status="active",
        usage_count=0,
        max_uses=1,
        can_be_used=True,
        created_at=datetime.utcnow()
    )


@router.get("/{prescription_id}/file")
async def get_prescription_file(
    prescription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get presigned URL for prescription file."""
    # In production: generate presigned S3 URL
    return {
        "prescription_id": prescription_id,
        "file_url": "https://s3.example.com/prescriptions/rx-001/prescription.jpg?signature=xyz",
        "expires_in": 3600
    }


@router.delete("/{prescription_id}")
async def delete_prescription(
    prescription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete (soft delete) a prescription."""
    # In production: soft delete from database
    return {"message": "Prescription deleted"}


@router.post("/{prescription_id}/validate")
async def validate_prescription(
    prescription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Re-validate a prescription."""
    # In production: re-run validation
    return {
        "prescription_id": prescription_id,
        "validation_status": "valid",
        "message": "Prescription validated successfully"
    }


@router.get("/{prescription_id}/items")
async def get_prescription_items(
    prescription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get items on a prescription."""
    return [
        {
            "id": "rx-item-001",
            "prescription_id": prescription_id,
            "medicine_name": "Amoxicillin 500mg",
            "dosage": "500mg",
            "quantity": 21,
            "instructions": "Take 1 capsule three times daily for 7 days",
            "refills_allowed": 0
        }
    ]


@router.post("/{prescription_id}/request-refill")
async def request_refill(
    prescription_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Request a refill for a prescription."""
    # In production: check refills remaining, create order
    return {
        "prescription_id": prescription_id,
        "refill_request_id": "rr-001",
        "status": "pending",
        "message": "Refill request submitted. A pharmacist will review it."
    }


# Pharmacist endpoints
@router.get("/pharmacist/review-queue")
async def get_review_queue(
    priority: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get prescriptions waiting for pharmacist review. (Pharmacist only)"""
    # In production: check role, query database
    return {
        "pending_reviews": 5,
        "prescriptions": [
            {
                "id": "rx-002",
                "priority": "high",
                "uploaded_at": datetime.utcnow().isoformat(),
                "validation_confidence": 0.75,
                "flags": ["controlled_substance"]
            }
        ]
    }


@router.post("/pharmacist/{prescription_id}/review")
async def review_prescription(
    prescription_id: str,
    status: str = Query(..., enum=["approved", "rejected", "needs_info"]),
    notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Review a prescription. (Pharmacist only)"""
    return {
        "prescription_id": prescription_id,
        "review_status": status,
        "reviewed_by": current_user["id"],
        "reviewed_at": datetime.utcnow().isoformat(),
        "notes": notes
    }
