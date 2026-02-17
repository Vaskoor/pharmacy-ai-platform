"""
Medicine catalog API routes.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
from decimal import Decimal

from app.api.auth import get_current_user

router = APIRouter(prefix="/medicines", tags=["Medicines"])


# Pydantic models
class MedicineResponse(BaseModel):
    id: str
    sku: str
    name: str
    generic_name: Optional[str]
    description: Optional[str]
    category_id: Optional[str]
    manufacturer: Optional[str]
    prescription_required: bool
    price: float
    compare_at_price: Optional[float]
    image_url: Optional[str]
    is_active: bool
    is_featured: bool
    slug: Optional[str]


class MedicineDetailResponse(MedicineResponse):
    active_ingredients: List[dict]
    inactive_ingredients: List[str]
    dosage_form: Optional[str]
    strength: Optional[str]
    indications: Optional[str]
    warnings: Optional[str]
    contraindications: Optional[str]
    side_effects: List[str]
    drug_interactions: List[str]


class CategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    parent_id: Optional[str]
    icon_url: Optional[str]
    display_order: int


class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    in_stock_only: bool = True
    otc_only: bool = False


# Sample data (would come from database in production)
SAMPLE_MEDICINES = [
    {
        "id": "med-001",
        "sku": "ADV-200-001",
        "name": "Advil Pain Reliever",
        "generic_name": "Ibuprofen",
        "description": "Pain reliever and fever reducer",
        "category_id": "cat-001",
        "manufacturer": "Pfizer",
        "prescription_required": False,
        "price": 12.99,
        "compare_at_price": 15.99,
        "image_url": "https://example.com/advil.jpg",
        "is_active": True,
        "is_featured": True,
        "slug": "advil-pain-reliever"
    },
    {
        "id": "med-002",
        "sku": "TYL-500-001",
        "name": "Tylenol Extra Strength",
        "generic_name": "Acetaminophen",
        "description": "Fast pain relief",
        "category_id": "cat-001",
        "manufacturer": "Johnson & Johnson",
        "prescription_required": False,
        "price": 9.99,
        "compare_at_price": None,
        "image_url": "https://example.com/tylenol.jpg",
        "is_active": True,
        "is_featured": True,
        "slug": "tylenol-extra-strength"
    },
    {
        "id": "med-003",
        "sku": "CLA-10-001",
        "name": "Claritin Allergy Relief",
        "generic_name": "Loratadine",
        "description": "24-hour allergy relief",
        "category_id": "cat-003",
        "manufacturer": "Bayer",
        "prescription_required": False,
        "price": 19.99,
        "compare_at_price": 24.99,
        "image_url": "https://example.com/claritin.jpg",
        "is_active": True,
        "is_featured": False,
        "slug": "claritin-allergy-relief"
    },
    {
        "id": "med-004",
        "sku": "AMX-500-001",
        "name": "Amoxicillin 500mg",
        "generic_name": "Amoxicillin",
        "description": "Antibiotic for bacterial infections",
        "category_id": "cat-007",
        "manufacturer": "Teva",
        "prescription_required": True,
        "price": 15.99,
        "compare_at_price": None,
        "image_url": "https://example.com/amoxicillin.jpg",
        "is_active": True,
        "is_featured": False,
        "slug": "amoxicillin-500mg"
    }
]

SAMPLE_CATEGORIES = [
    {"id": "cat-001", "name": "Pain Relief", "description": "Pain management medicines", "parent_id": None, "icon_url": None, "display_order": 1},
    {"id": "cat-002", "name": "Cold & Flu", "description": "Cold and flu remedies", "parent_id": None, "icon_url": None, "display_order": 2},
    {"id": "cat-003", "name": "Allergy", "description": "Allergy relief medicines", "parent_id": None, "icon_url": None, "display_order": 3},
    {"id": "cat-007", "name": "Prescription Medications", "description": "Prescription-only medicines", "parent_id": None, "icon_url": None, "display_order": 7},
]


@router.get("", response_model=List[MedicineResponse])
async def list_medicines(
    category: Optional[str] = Query(None, description="Filter by category ID"),
    search: Optional[str] = Query(None, description="Search query"),
    prescription_required: Optional[bool] = Query(None),
    in_stock: Optional[bool] = Query(True),
    featured: Optional[bool] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    sort_by: str = Query("name", enum=["name", "price", "popularity"]),
    sort_order: str = Query("asc", enum=["asc", "desc"]),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """List medicines with filtering and pagination."""
    medicines = SAMPLE_MEDICINES.copy()
    
    # Apply filters
    if category:
        medicines = [m for m in medicines if m["category_id"] == category]
    
    if search:
        search_lower = search.lower()
        medicines = [
            m for m in medicines 
            if search_lower in m["name"].lower() 
            or search_lower in (m.get("generic_name") or "").lower()
        ]
    
    if prescription_required is not None:
        medicines = [m for m in medicines if m["prescription_required"] == prescription_required]
    
    if featured is not None:
        medicines = [m for m in medicines if m["is_featured"] == featured]
    
    if min_price is not None:
        medicines = [m for m in medicines if m["price"] >= min_price]
    
    if max_price is not None:
        medicines = [m for m in medicines if m["price"] <= max_price]
    
    # Sort
    reverse = sort_order == "desc"
    if sort_by == "price":
        medicines.sort(key=lambda x: x["price"], reverse=reverse)
    else:
        medicines.sort(key=lambda x: x["name"], reverse=reverse)
    
    # Paginate
    total = len(medicines)
    medicines = medicines[offset:offset + limit]
    
    return medicines


@router.get("/search")
async def search_medicines(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Search medicines by name, generic name, or description."""
    query_lower = q.lower()
    
    results = [
        m for m in SAMPLE_MEDICINES
        if query_lower in m["name"].lower()
        or query_lower in (m.get("generic_name") or "").lower()
        or query_lower in (m.get("description") or "").lower()
    ]
    
    return {
        "query": q,
        "results": results[:limit],
        "total": len(results)
    }


@router.get("/featured", response_model=List[MedicineResponse])
async def get_featured_medicines(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Get featured medicines."""
    featured = [m for m in SAMPLE_MEDICINES if m["is_featured"]]
    return featured[:limit]


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    parent_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """List medicine categories."""
    categories = SAMPLE_CATEGORIES
    
    if parent_id:
        categories = [c for c in categories if c["parent_id"] == parent_id]
    
    return categories


@router.get("/{medicine_id}", response_model=MedicineResponse)
async def get_medicine(
    medicine_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get medicine details by ID."""
    medicine = next((m for m in SAMPLE_MEDICINES if m["id"] == medicine_id), None)
    
    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found"
        )
    
    return medicine


@router.get("/{medicine_id}/details", response_model=MedicineDetailResponse)
async def get_medicine_details(
    medicine_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed medicine information."""
    medicine = next((m for m in SAMPLE_MEDICINES if m["id"] == medicine_id), None)
    
    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found"
        )
    
    # Add detailed info
    details = {
        **medicine,
        "active_ingredients": [{"name": "Ibuprofen", "strength": "200mg"}],
        "inactive_ingredients": ["corn starch", "croscarmellose sodium"],
        "dosage_form": "tablet",
        "strength": "200mg",
        "indications": "For temporary relief of minor aches and pains",
        "warnings": "Do not use if allergic to ibuprofen",
        "contraindications": "Pregnancy third trimester",
        "side_effects": ["Stomach upset", "Heartburn", "Dizziness"],
        "drug_interactions": ["Blood thinners", "Aspirin"]
    }
    
    return details


@router.get("/{medicine_id}/alternatives")
async def get_medicine_alternatives(
    medicine_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get alternative medicines (same generic)."""
    medicine = next((m for m in SAMPLE_MEDICINES if m["id"] == medicine_id), None)
    
    if not medicine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found"
        )
    
    # Find alternatives with same generic name
    alternatives = [
        m for m in SAMPLE_MEDICINES
        if m.get("generic_name") == medicine.get("generic_name")
        and m["id"] != medicine_id
    ]
    
    return {
        "medicine_id": medicine_id,
        "alternatives": alternatives
    }


@router.post("/{medicine_id}/check-interactions")
async def check_interactions(
    medicine_id: str,
    other_medicine_ids: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Check for drug interactions."""
    # In production: query drug interaction database
    return {
        "medicine_id": medicine_id,
        "other_medicines": other_medicine_ids,
        "has_interactions": False,
        "interactions": [],
        "recommendation": "No known interactions. Consult your pharmacist for confirmation."
    }


@router.get("/{medicine_id}/inventory")
async def get_inventory(
    medicine_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get inventory status for a medicine."""
    # In production: query inventory database
    return {
        "medicine_id": medicine_id,
        "quantity_available": 100,
        "quantity_reserved": 5,
        "quantity_on_hand": 95,
        "reorder_level": 20,
        "is_low_stock": False,
        "in_stock": True
    }
