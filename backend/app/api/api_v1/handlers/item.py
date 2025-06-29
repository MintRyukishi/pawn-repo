# backend/app/api/api_v1/handlers/item.py (SIMPLIFIED VERSION)
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from uuid import UUID
from app.schemas.item_schema import ItemCreate, ItemUpdate, ItemOut, ItemSearch, ItemReceipt
from app.models.item_model import ItemStatus
from app.services.item_service import ItemService
from app.api.deps.user_deps import get_current_user
from app.models.user_model import User
import logging

logger = logging.getLogger(__name__)
item_router = APIRouter()

@item_router.post("/", summary="Create a new item", response_model=ItemOut)
async def create_item(
    item_data: ItemCreate,
    current_user: User = Depends(get_current_user)
):
    try:
        item = await ItemService.create_item(item_data, current_user.user_id)
        return item
    except Exception as e:
        logger.error(f"Error creating item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create item"
        )

@item_router.get("/{item_id}", summary="Get item by ID", response_model=ItemOut)
async def get_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user)
):
    item = await ItemService.get_item_by_id(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    return item

@item_router.put("/{item_id}", summary="Update item", response_model=ItemOut)
async def update_item(
    item_id: UUID,
    item_data: ItemUpdate,
    current_user: User = Depends(get_current_user)
):
    try:
        item = await ItemService.update_item(item_id, item_data)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        return item
    except Exception as e:
        logger.error(f"Error updating item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update item"
        )

@item_router.delete("/{item_id}", summary="Delete item")
async def delete_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user)
):
    success = await ItemService.delete_item(item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    return {"message": "Item deleted successfully"}

@item_router.get("/", summary="Search items", response_model=List[ItemOut])
async def search_items(
    description: Optional[str] = Query(None, description="Search by item description"),
    status: Optional[ItemStatus] = Query(None, description="Filter by status"),
    customer_id: Optional[UUID] = Query(None, description="Filter by customer"),
    serial_number: Optional[str] = Query(None, description="Search by serial number"),
    storage_location: Optional[str] = Query(None, description="Search by storage location"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    try:
        search_params = ItemSearch(
            description=description,
            status=status,
            customer_id=customer_id,
            serial_number=serial_number,
            storage_location=storage_location
        )
        items = await ItemService.search_items(search_params, skip, limit)
        return items
    except Exception as e:
        logger.error(f"Error searching items: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search items"
        )

@item_router.get("/customer/{customer_id}", summary="Get items by customer", response_model=List[ItemOut])
async def get_items_by_customer(
    customer_id: UUID,
    status: Optional[ItemStatus] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user)
):
    try:
        items = await ItemService.get_items_by_customer(customer_id, status)
        return items
    except Exception as e:
        logger.error(f"Error fetching items for customer {customer_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch customer items"
        )

@item_router.patch("/{item_id}/redeem", summary="Mark item as redeemed", response_model=ItemOut)
async def redeem_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user)
):
    try:
        item = await ItemService.mark_as_redeemed(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        return item
    except Exception as e:
        logger.error(f"Error redeeming item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to redeem item"
        )

@item_router.patch("/{item_id}/forfeit", summary="Mark item as forfeited", response_model=ItemOut)
async def forfeit_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user)
):
    try:
        item = await ItemService.mark_as_forfeited(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        return item
    except Exception as e:
        logger.error(f"Error forfeiting item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to forfeit item"
        )

@item_router.get("/{item_id}/receipt", summary="Get item info for customer receipt", response_model=ItemReceipt)
async def get_item_for_receipt(
    item_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get item information formatted for customer receipt (excludes internal notes)"""
    item = await ItemService.get_item_by_id(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return ItemReceipt(
        description=item.description,
        serial_number=item.serial_number,
        loan_amount=item.loan_amount
    )