# backend/app/services/customer_service.py - CLEANED VERSION
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.customer_model import Customer, CustomerStatus
from app.schemas.customer_schema import CustomerCreate, CustomerUpdate, CustomerSearch, CustomerStatusUpdate
from app.utils.phone_utils import normalize_phone_number  # Use centralized utility
from beanie import PydanticObjectId
from beanie.operators import RegEx, Or, And
import re

def parse_name_query(query: str) -> dict:
    """
    Parse name query to handle different formats:
    - "sar" -> search first OR last name starting with "sar"
    - "sar joh" -> search first name starting with "sar" AND last name starting with "joh"
    - "joh smi" -> search first name starting with "joh" AND last name starting with "smi"
    """
    query = query.strip().lower()
    parts = query.split()
    
    if len(parts) == 1:
        # Single word - search either first OR last name
        return {
            "type": "single",
            "query": parts[0]
        }
    elif len(parts) == 2:
        # Two words - first name AND last name
        return {
            "type": "combination", 
            "first_name": parts[0],
            "last_name": parts[1]
        }
    else:
        # More than 2 words - treat as single query
        return {
            "type": "single",
            "query": " ".join(parts)
        }

class CustomerService:
    @staticmethod
    async def create_customer(customer_data: CustomerCreate) -> Customer:
        # Use centralized phone normalization
        normalized_phone = normalize_phone_number(customer_data.phone)
        customer_dict = customer_data.dict()
        customer_dict['phone'] = normalized_phone
        
        customer = Customer(**customer_dict)
        await customer.save()
        return customer

    @staticmethod
    async def get_customer_by_id(customer_id: UUID) -> Optional[Customer]:
        return await Customer.find_one(Customer.customer_id == customer_id)

    @staticmethod
    async def get_customer_by_phone(phone: str) -> Optional[Customer]:
        # Use centralized phone normalization
        normalized_phone = normalize_phone_number(phone)
        return await Customer.find_one(Customer.phone == normalized_phone)

    @staticmethod
    async def update_customer(customer_id: UUID, customer_data: CustomerUpdate) -> Optional[Customer]:
        customer = await CustomerService.get_customer_by_id(customer_id)
        if not customer:
            return None
        
        update_data = customer_data.dict(exclude_unset=True)
        
        # Use centralized phone normalization
        if 'phone' in update_data and update_data['phone']:
            update_data['phone'] = normalize_phone_number(update_data['phone'])
        
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            await customer.update({"$set": update_data})
            return await CustomerService.get_customer_by_id(customer_id)
        return customer

    @staticmethod
    async def update_customer_status(customer_id: UUID, status_data: CustomerStatusUpdate, changed_by: UUID) -> Optional[Customer]:
        """Update customer status with reason and audit trail"""
        customer = await CustomerService.get_customer_by_id(customer_id)
        if not customer:
            return None
        
        update_data = {
            "status": status_data.status,
            "status_reason": status_data.reason,
            "status_changed_at": datetime.utcnow(),
            "status_changed_by": changed_by,
            "updated_at": datetime.utcnow()
        }
        
        # Handle suspension logic
        if status_data.status == CustomerStatus.SUSPENDED:
            update_data["suspension_until"] = status_data.suspension_until
        else:
            update_data["suspension_until"] = None
        
        # Update is_active for backward compatibility
        update_data["is_active"] = status_data.status == CustomerStatus.ACTIVE
        
        await customer.update({"$set": update_data})
        return await CustomerService.get_customer_by_id(customer_id)

    @staticmethod
    async def delete_customer(customer_id: UUID) -> bool:
        customer = await CustomerService.get_customer_by_id(customer_id)
        if customer:
            await customer.delete()
            return True
        return False

    @staticmethod
    async def search_customers(search_params: CustomerSearch, skip: int = 0, limit: int = 50) -> List[Customer]:
        query_conditions = []
        
        # Handle new status filter
        if search_params.status:
            query_conditions.append(Customer.status == search_params.status)
        elif search_params.is_active is not None:
            # Backward compatibility
            query_conditions.append(Customer.is_active == search_params.is_active)
        
        if search_params.phone:
            # Use centralized phone normalization
            normalized_phone = normalize_phone_number(search_params.phone)
            query_conditions.append(Customer.phone == normalized_phone)
            
        if search_params.query:
            # Check if it's an email search
            if "@" in search_params.query:
                query_conditions.append(RegEx(Customer.email, search_params.query, "i"))
            else:
                # Parse the name query
                parsed = parse_name_query(search_params.query)
                
                if parsed["type"] == "single":
                    # Single word - require minimum 3 characters
                    if len(parsed["query"]) >= 3:
                        # Search first name OR last name starting with query
                        name_conditions = [
                            RegEx(Customer.first_name, f"^{re.escape(parsed['query'])}", "i"),
                            RegEx(Customer.last_name, f"^{re.escape(parsed['query'])}", "i"),
                        ]
                        query_conditions.append(Or(*name_conditions))
                        
                elif parsed["type"] == "combination":
                    # Two words - first name AND last name
                    first_name_query = parsed["first_name"]
                    last_name_query = parsed["last_name"]
                    
                    # Both parts must be at least 3 characters
                    if len(first_name_query) >= 3 and len(last_name_query) >= 3:
                        # First name starts with first part AND last name starts with second part
                        combination_conditions = [
                            RegEx(Customer.first_name, f"^{re.escape(first_name_query)}", "i"),
                            RegEx(Customer.last_name, f"^{re.escape(last_name_query)}", "i")
                        ]
                        query_conditions.append(And(*combination_conditions))
        
        if query_conditions:
            query = Customer.find(And(*query_conditions))
        else:
            query = Customer.find()
            
        return await query.skip(skip).limit(limit).to_list()

    @staticmethod
    async def get_customer_count(search_params: CustomerSearch) -> int:
        query_conditions = []
        
        # Handle new status filter
        if search_params.status:
            query_conditions.append(Customer.status == search_params.status)
        elif search_params.is_active is not None:
            # Backward compatibility
            query_conditions.append(Customer.is_active == search_params.is_active)
        
        if search_params.phone:
            normalized_phone = normalize_phone_number(search_params.phone)
            query_conditions.append(Customer.phone == normalized_phone)
            
        if search_params.query:
            if "@" in search_params.query:
                query_conditions.append(RegEx(Customer.email, search_params.query, "i"))
            else:
                parsed = parse_name_query(search_params.query)
                
                if parsed["type"] == "single":
                    if len(parsed["query"]) >= 3:
                        name_conditions = [
                            RegEx(Customer.first_name, f"^{re.escape(parsed['query'])}", "i"),
                            RegEx(Customer.last_name, f"^{re.escape(parsed['query'])}", "i"),
                        ]
                        query_conditions.append(Or(*name_conditions))
                        
                elif parsed["type"] == "combination":
                    first_name_query = parsed["first_name"]
                    last_name_query = parsed["last_name"]
                    
                    if len(first_name_query) >= 3 and len(last_name_query) >= 3:
                        combination_conditions = [
                            RegEx(Customer.first_name, f"^{re.escape(first_name_query)}", "i"),
                            RegEx(Customer.last_name, f"^{re.escape(last_name_query)}", "i")
                        ]
                        query_conditions.append(And(*combination_conditions))
        
        if query_conditions:
            return await Customer.find(And(*query_conditions)).count()
        else:
            return await Customer.find().count()

    @staticmethod
    async def search_customers_by_name_partial(name_query: str, skip: int = 0, limit: int = 50) -> List[Customer]:
        """
        Dedicated method for partial name search supporting both single and combination formats
        """
        parsed = parse_name_query(name_query)
        
        if parsed["type"] == "single":
            if len(parsed["query"]) < 3:
                return []
            
            # Search for names that start with the query (case insensitive)
            name_conditions = [
                RegEx(Customer.first_name, f"^{re.escape(parsed['query'])}", "i"),
                RegEx(Customer.last_name, f"^{re.escape(parsed['query'])}", "i"),
            ]
            
            query = Customer.find(
                And(
                    Customer.status == CustomerStatus.ACTIVE,
                    Or(*name_conditions)
                )
            )
            
        elif parsed["type"] == "combination":
            first_name_query = parsed["first_name"]
            last_name_query = parsed["last_name"]
            
            if len(first_name_query) < 3 or len(last_name_query) < 3:
                return []
            
            # Search for exact combination
            combination_conditions = [
                RegEx(Customer.first_name, f"^{re.escape(first_name_query)}", "i"),
                RegEx(Customer.last_name, f"^{re.escape(last_name_query)}", "i")
            ]
            
            query = Customer.find(
                And(
                    Customer.status == CustomerStatus.ACTIVE,
                    *combination_conditions
                )
            )
        else:
            return []
        
        return await query.skip(skip).limit(limit).to_list()

    @staticmethod
    async def get_customers_by_status(status: CustomerStatus, skip: int = 0, limit: int = 50) -> List[Customer]:
        """Get customers by their status"""
        return await Customer.find(Customer.status == status).skip(skip).limit(limit).to_list()

    @staticmethod
    async def check_customer_can_transact(customer_id: UUID) -> bool:
        """Check if customer can make new transactions"""
        customer = await CustomerService.get_customer_by_id(customer_id)
        if not customer:
            return False
        return customer.can_transact

    @staticmethod
    async def auto_restore_suspended_customers() -> List[Customer]:
        """Automatically restore customers whose suspension period has ended"""
        now = datetime.utcnow()
        
        # Find suspended customers whose suspension has expired
        expired_suspensions = await Customer.find(
            And(
                Customer.status == CustomerStatus.SUSPENDED,
                Customer.suspension_until <= now
            )
        ).to_list()
        
        restored_customers = []
        for customer in expired_suspensions:
            # Restore to active status
            await customer.update({
                "$set": {
                    "status": CustomerStatus.ACTIVE,
                    "status_reason": "Suspension period expired - automatically restored",
                    "status_changed_at": now,
                    "suspension_until": None,
                    "is_active": True,
                    "updated_at": now
                }
            })
            restored_customers.append(customer)
        
        return restored_customers