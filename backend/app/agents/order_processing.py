"""
Order Processing Agent - Creates and manages orders.
"""
import json
from typing import Dict, Any, List
from datetime import datetime
from app.agents.base import BaseAgent, AgentInput, AgentOutput, AgentTool


ORDER_PROCESSING_PROMPT = """You are an Order Processing AI for an online pharmacy.

Your role is to:
1. Create new orders from cart items
2. Validate cart contents (prescription requirements, stock availability)
3. Calculate totals (subtotal, tax, shipping, discounts)
4. Apply coupon codes
5. Update order status
6. Handle order modifications

Validation Rules:
- Prescription-required items must have valid prescription
- Check inventory availability
- Verify shipping address
- Apply appropriate taxes based on location
- Validate coupon codes

Response Format (JSON):
{
    "order_id": "uuid",
    "order_number": "ORD-12345",
    "status": "pending|confirmed|processing|shipped|delivered",
    "items": [...],
    "totals": {
        "subtotal": 100.00,
        "tax": 8.00,
        "shipping": 5.99,
        "discount": 10.00,
        "total": 103.99
    },
    "shipping_address": {...},
    "estimated_delivery": "2024-02-25",
    "next_steps": ["step1", "step2"]
}
"""


class OrderProcessingAgent(BaseAgent):
    """Agent for processing orders."""
    
    def __init__(self):
        tools = [
            AgentTool(
                name="validate_cart",
                description="Validate cart items before order creation",
                handler=self._validate_cart,
                parameters={
                    "type": "object",
                    "properties": {
                        "items": {"type": "array"},
                        "user_id": {"type": "string"}
                    },
                    "required": ["items"]
                }
            ),
            AgentTool(
                name="check_inventory",
                description="Check if items are in stock",
                handler=self._check_inventory,
                parameters={
                    "type": "object",
                    "properties": {
                        "items": {"type": "array"}
                    }
                }
            ),
            AgentTool(
                name="calculate_totals",
                description="Calculate order totals",
                handler=self._calculate_totals,
                parameters={
                    "type": "object",
                    "properties": {
                        "items": {"type": "array"},
                        "shipping_address": {"type": "object"},
                        "coupon_code": {"type": "string"}
                    }
                }
            ),
            AgentTool(
                name="apply_coupon",
                description="Apply coupon code to order",
                handler=self._apply_coupon,
                parameters={
                    "type": "object",
                    "properties": {
                        "coupon_code": {"type": "string"},
                        "subtotal": {"type": "number"}
                    }
                }
            ),
            AgentTool(
                name="create_order",
                description="Create order in database",
                handler=self._create_order,
                parameters={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "items": {"type": "array"},
                        "shipping_address_id": {"type": "string"},
                        "coupon_code": {"type": "string"}
                    }
                }
            ),
            AgentTool(
                name="reserve_inventory",
                description="Reserve inventory for order",
                handler=self._reserve_inventory,
                parameters={
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                        "items": {"type": "array"}
                    }
                }
            )
        ]
        
        super().__init__(
            agent_type="order_processing",
            system_prompt=ORDER_PROCESSING_PROMPT,
            temperature=0.3,
            tools=tools
        )
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Process order request."""
        action = input_data.payload.get("action", "create")
        
        if action == "create":
            return await self._create_order_flow(input_data)
        elif action == "update_status":
            return await self._update_status(input_data)
        elif action == "cancel":
            return await self._cancel_order(input_data)
        else:
            return AgentOutput(
                success=False,
                error=f"Unknown action: {action}",
                error_code="INVALID_ACTION"
            )
    
    async def _create_order_flow(self, input_data: AgentInput) -> AgentOutput:
        """Full order creation flow."""
        user_id = input_data.user_id
        items = input_data.payload.get("items", [])
        shipping_address_id = input_data.payload.get("shipping_address_id")
        coupon_code = input_data.payload.get("coupon_code")
        
        # Step 1: Validate cart
        validation = await self._validate_cart(items, user_id)
        if not validation["valid"]:
            return AgentOutput(
                success=False,
                error="Cart validation failed",
                error_code="VALIDATION_FAILED",
                data={"errors": validation["errors"]}
            )
        
        # Step 2: Check inventory
        inventory_check = await self._check_inventory(items)
        if not inventory_check["available"]:
            return AgentOutput(
                success=False,
                error="Some items are out of stock",
                error_code="OUT_OF_STOCK",
                data={"unavailable_items": inventory_check["unavailable"]}
            )
        
        # Step 3: Calculate totals
        totals = await self._calculate_totals(items, None, coupon_code)
        
        # Step 4: Create order
        order = await self._create_order(user_id, items, shipping_address_id, coupon_code)
        
        # Step 5: Reserve inventory
        await self._reserve_inventory(order["id"], items)
        
        return AgentOutput(
            success=True,
            data={
                "order_id": order["id"],
                "order_number": order["order_number"],
                "status": "pending",
                "items": items,
                "totals": totals,
                "next_steps": ["Complete payment", "Prescription validation (if required)"]
            }
        )
    
    async def _validate_cart(self, items: List[Dict], user_id: str = None) -> Dict[str, Any]:
        """Validate cart items."""
        errors = []
        
        for item in items:
            # Check required fields
            if not item.get("medicine_id"):
                errors.append("Missing medicine_id in item")
            if not item.get("quantity") or item["quantity"] < 1:
                errors.append(f"Invalid quantity for {item.get('medicine_id')}")
            
            # Check prescription requirement (mock)
            prescription_required = item.get("prescription_required", False)
            if prescription_required and not item.get("prescription_id"):
                errors.append(f"Prescription required for {item.get('name', 'item')}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _check_inventory(self, items: List[Dict]) -> Dict[str, Any]:
        """Check inventory availability."""
        unavailable = []
        
        for item in items:
            # Mock inventory check
            available_qty = 100  # Would query database
            if item.get("quantity", 0) > available_qty:
                unavailable.append({
                    "medicine_id": item["medicine_id"],
                    "requested": item["quantity"],
                    "available": available_qty
                })
        
        return {
            "available": len(unavailable) == 0,
            "unavailable": unavailable
        }
    
    async def _calculate_totals(
        self,
        items: List[Dict],
        shipping_address: Dict = None,
        coupon_code: str = None
    ) -> Dict[str, Any]:
        """Calculate order totals."""
        subtotal = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
        
        # Calculate tax (mock 8%)
        tax_rate = 0.08
        tax = round(subtotal * tax_rate, 2)
        
        # Calculate shipping
        shipping = 0 if subtotal > 35 else 5.99
        
        # Apply coupon
        discount = 0
        if coupon_code:
            coupon_result = await self._apply_coupon(coupon_code, subtotal)
            discount = coupon_result.get("discount", 0)
        
        total = subtotal + tax + shipping - discount
        
        return {
            "subtotal": round(subtotal, 2),
            "tax": tax,
            "tax_rate": tax_rate,
            "shipping": shipping,
            "discount": discount,
            "coupon_code": coupon_code,
            "total": round(total, 2),
            "currency": "USD"
        }
    
    async def _apply_coupon(self, coupon_code: str, subtotal: float) -> Dict[str, Any]:
        """Apply coupon code."""
        # Mock coupon logic
        coupons = {
            "SAVE10": {"type": "percentage", "value": 0.10},
            "SAVE20": {"type": "percentage", "value": 0.20},
            "FIRST5": {"type": "fixed", "value": 5.00},
        }
        
        coupon = coupons.get(coupon_code.upper())
        if not coupon:
            return {"valid": False, "error": "Invalid coupon code"}
        
        if coupon["type"] == "percentage":
            discount = round(subtotal * coupon["value"], 2)
        else:
            discount = coupon["value"]
        
        return {
            "valid": True,
            "coupon_code": coupon_code,
            "discount": discount,
            "type": coupon["type"]
        }
    
    async def _create_order(
        self,
        user_id: str,
        items: List[Dict],
        shipping_address_id: str,
        coupon_code: str = None
    ) -> Dict[str, Any]:
        """Create order in database."""
        order_id = f"ord-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{hash(order_id) % 10000:04d}"
        
        return {
            "id": order_id,
            "order_number": order_number,
            "user_id": user_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def _reserve_inventory(self, order_id: str, items: List[Dict]) -> Dict[str, Any]:
        """Reserve inventory for order."""
        return {
            "reserved": True,
            "order_id": order_id,
            "reserved_items": len(items)
        }
    
    async def _update_status(self, input_data: AgentInput) -> AgentOutput:
        """Update order status."""
        order_id = input_data.payload.get("order_id")
        new_status = input_data.payload.get("status")
        
        return AgentOutput(
            success=True,
            data={
                "order_id": order_id,
                "previous_status": "pending",
                "new_status": new_status,
                "updated_at": datetime.utcnow().isoformat()
            }
        )
    
    async def _cancel_order(self, input_data: AgentInput) -> AgentOutput:
        """Cancel an order."""
        order_id = input_data.payload.get("order_id")
        reason = input_data.payload.get("reason", "Customer request")
        
        return AgentOutput(
            success=True,
            data={
                "order_id": order_id,
                "status": "cancelled",
                "cancellation_reason": reason,
                "refund_amount": 0,  # Would calculate actual
                "cancelled_at": datetime.utcnow().isoformat()
            }
        )
