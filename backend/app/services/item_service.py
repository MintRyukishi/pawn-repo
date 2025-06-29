# backend/app/services/item_service.py (SIMPLIFIED VERSION)
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.item_model import Item, ItemStatus
from app.schemas.item_schema import ItemCreate, ItemUpdate, ItemSearch
from beanie.operators import RegEx, And
import logging

logger = logging.getLogger(__name__)

class ItemService:
    @staticmethod
    async def create_item(item_data: ItemCreate, created_by: UUID) -> Item:
        item_dict = item_data.dict()
        item_dict['created_by'] = created_by
        
        item = Item(**item_dict)
        await item.save()
        return item

    @staticmethod
    async def get_item_by_id(item_id: UUID) -> Optional[Item]:
        return await Item.find_one(Item.item_id == item_id)

    @staticmethod
    async def update_item(item_id: UUID, item_data: ItemUpdate) -> Optional[Item]:
        item = await ItemService.get_item_by_id(item_id)
        if not item:
            return None
        
        update_data = item_data.dict(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            await item.update({"$set": update_data})
            return await ItemService.get_item_by_id(item_id)
        return item

    @staticmethod
    async def delete_item(item_id: UUID) -> bool:
        item = await ItemService.get_item_by_id(item_id)
        if item:
            await item.delete()
            return True
        return False

    @staticmethod
    async def search_items(search_params: ItemSearch, skip: int = 0, limit: int = 50) -> List[Item]:
        query_conditions = []
        
        if search_params.description:
            # Simple text search in description
            query_conditions.append(RegEx(Item.description, search_params.description, "i"))
        
        if search_params.status:
            query_conditions.append(Item.status == search_params.status)
        
        if search_params.customer_id:
            query_conditions.append(Item.customer_id == search_params.customer_id)
        
        if search_params.serial_number:
            query_conditions.append(RegEx(Item.serial_number, search_params.serial_number, "i"))
        
        if search_params.storage_location:
            query_conditions.append(RegEx(Item.storage_location, search_params.storage_location, "i"))
        
        if query_conditions:
            query = Item.find(And(*query_conditions))
        else:
            query = Item.find()
            
        return await query.skip(skip).limit(limit).to_list()

    @staticmethod
    async def get_items_by_customer(customer_id: UUID, status: Optional[ItemStatus] = None) -> List[Item]:
        query_conditions = [Item.customer_id == customer_id]
        
        if status:
            query_conditions.append(Item.status == status)
        
        return await Item.find(And(*query_conditions)).to_list()

    @staticmethod
    async def mark_as_redeemed(item_id: UUID) -> Optional[Item]:
        """Mark item as redeemed by customer"""
        return await ItemService.update_item_status(item_id, ItemStatus.REDEEMED)

    @staticmethod
    async def mark_as_forfeited(item_id: UUID) -> Optional[Item]:
        """Mark item as forfeited (becomes shop property)"""
        return await ItemService.update_item_status(item_id, ItemStatus.FORFEITED)

    @staticmethod
    async def update_item_status(item_id: UUID, status: ItemStatus) -> Optional[Item]:
        item = await ItemService.get_item_by_id(item_id)
        if not item:
            return None
        
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        await item.update({"$set": update_data})
        return await ItemService.get_item_by_id(item_id)

    @staticmethod
    async def get_active_items_count() -> int:
        return await Item.find(Item.status == ItemStatus.ACTIVE).count()

    @staticmethod
    async def get_total_active_loans() -> float:
        """Get total amount of active loans"""
        active_items = await Item.find(Item.status == ItemStatus.ACTIVE).to_list()
        return sum(item.loan_amount for item in active_items)