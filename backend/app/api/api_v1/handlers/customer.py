# backend/app/api/api_v1/handlers/customer.py
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.schemas.customer_schema import (
    CustomerCreate, CustomerUpdate, CustomerOut, CustomerSearch, CustomerStatusUpdate
)
from app.models.customer_model import CustomerStatus
from app.services.customer_service import CustomerService
from app.api.deps.user_deps import get_current_user
from app.models.user_model import User
import pymongo

customer_router = APIRouter()

@customer_router.post("/", summary="Create a new customer", response_model=CustomerOut)
async def create_customer(
    customer_data: CustomerCreate,
    current_user: User = Depends(get_current_user)
):
    try:
        customer = await CustomerService.create_customer(customer_data)
        return customer
    except pymongo.errors.DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer with this phone number already exists"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@customer_router.get("/{customer_id}", summary="Get customer by ID", response_model=CustomerOut)
async def get_customer(
    customer_id: UUID,
    current_user: User = Depends(get_current_user)
):
    customer = await CustomerService.get_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    return customer

@customer_router.put("/{customer_id}", summary="Update customer", response_model=CustomerOut)
async def update_customer(
    customer_id: UUID,
    customer_data: CustomerUpdate,
    current_user: User = Depends(get_current_user)
):
    try:
        customer = await CustomerService.update_customer(customer_id, customer_data)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        return customer
    except pymongo.errors.DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer with this phone number already exists"
        )

@customer_router.patch("/{customer_id}/status", summary="Update customer status", response_model=CustomerOut)
async def update_customer_status(
    customer_id: UUID,
    status_data: CustomerStatusUpdate,
    current_user: User = Depends(get_current_user)
):
    # Validate suspension logic
    if status_data.status == CustomerStatus.SUSPENDED and not status_data.suspension_until:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="suspension_until is required when status is 'suspended'"
        )
    
    if status_data.status != CustomerStatus.SUSPENDED and status_data.suspension_until:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="suspension_until should only be set when status is 'suspended'"
        )
    
    customer = await CustomerService.update_customer_status(
        customer_id, status_data, current_user.user_id
    )
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    return customer

@customer_router.delete("/{customer_id}", summary="Delete customer")
async def delete_customer(
    customer_id: UUID,
    current_user: User = Depends(get_current_user)
):
    success = await CustomerService.delete_customer(customer_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    return {"message": "Customer deleted successfully"}

@customer_router.patch("/{customer_id}/deactivate", summary="Deactivate customer (deprecated - use status update)", response_model=CustomerOut)
async def deactivate_customer(
    customer_id: UUID,
    current_user: User = Depends(get_current_user)
):
    customer = await CustomerService.deactivate_customer(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    return customer

@customer_router.get("/", summary="Search customers", response_model=List[CustomerOut])
async def search_customers(
    query: Optional[str] = Query(None, description="Search query (name or email) - min 3 chars for names"),
    phone: Optional[str] = Query(None, description="Search by phone number"),
    status: Optional[CustomerStatus] = Query(None, description="Filter by customer status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (deprecated)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    current_user: User = Depends(get_current_user)
):
    search_params = CustomerSearch(
        query=query,
        phone=phone,
        status=status,
        is_active=is_active
    )
    customers = await CustomerService.search_customers(search_params, skip, limit)
    return customers

@customer_router.get("/search/name/{name_query}", summary="Search customers by partial name (min 3 chars)", response_model=List[CustomerOut])
async def search_customers_by_name(
    name_query: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    current_user: User = Depends(get_current_user)
):
    if len(name_query.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name query must be at least 3 characters long"
        )
    
    customers = await CustomerService.search_customers_by_name_partial(name_query, skip, limit)
    return customers

@customer_router.get("/search/count", summary="Get customer count", response_model=dict)
async def get_customer_count(
    query: Optional[str] = Query(None, description="Search query"),
    phone: Optional[str] = Query(None, description="Search by phone number"),
    status: Optional[CustomerStatus] = Query(None, description="Filter by customer status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_user)
):
    search_params = CustomerSearch(
        query=query,
        phone=phone,
        status=status,
        is_active=is_active
    )
    count = await CustomerService.get_customer_count(search_params)
    return {"count": count}

@customer_router.get("/lookup/phone/{phone}", summary="Get customer by phone", response_model=CustomerOut)
async def get_customer_by_phone(
    phone: str,
    current_user: User = Depends(get_current_user)
):
    customer = await CustomerService.get_customer_by_phone(phone)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    return customer

@customer_router.get("/status/suspended", summary="Get suspended customers", response_model=List[CustomerOut])
async def get_suspended_customers(
    current_user: User = Depends(get_current_user)
):
    customers = await CustomerService.get_customers_by_status(CustomerStatus.SUSPENDED)
    return customers

@customer_router.get("/status/banned", summary="Get banned customers", response_model=List[CustomerOut])
async def get_banned_customers(
    current_user: User = Depends(get_current_user)
):
    customers = await CustomerService.get_customers_by_status(CustomerStatus.BANNED)
    return customers