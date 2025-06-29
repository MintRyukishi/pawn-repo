# backend/app/services/user_service.py
from typing import Optional, List
from uuid import UUID
from app.schemas.user_schema import UserAuth, UserUpdate
from app.models.user_model import User
from app.core.security import get_password, verify_password
import logging

logger = logging.getLogger(__name__)

class UserService:
    @staticmethod
    async def create_user(user: UserAuth):
        user_in = User(
            username=user.username,
            email=user.email,
            hashed_password=get_password(user.password),
        )
        await user_in.save()
        return user_in
    
    @staticmethod
    async def authenticate(email: str, password: str) -> Optional[User]:
        user = await UserService.get_user_by_email(email=email)
        if not user:
            return None
        if not verify_password(password=password, hashed_password=user.hashed_password):
            return None
        
        return user

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[User]:
        user = await User.find_one(User.email == email)
        return user
    
    @staticmethod
    async def get_user_by_id(id: UUID) -> Optional[User]:
        user = await User.find_one(User.user_id == id)
        return user

    @staticmethod
    async def get_user_by_username(username: str) -> Optional[User]:
        user = await User.find_one(User.username == username)
        return user

    @staticmethod
    async def get_all_users(skip: int = 0, limit: int = 100) -> List[User]:
        return await User.find().skip(skip).limit(limit).to_list()

    @staticmethod
    async def update_user(user_id: UUID, user_data: UserUpdate) -> Optional[User]:
        user = await UserService.get_user_by_id(user_id)
        if not user:
            return None
        
        update_data = user_data.dict(exclude_unset=True)
        if update_data:
            await user.update({"$set": update_data})
            return await UserService.get_user_by_id(user_id)
        return user

    @staticmethod
    async def delete_user(user_id: UUID) -> bool:
        user = await UserService.get_user_by_id(user_id)
        if user:
            await user.delete()
            return True
        return False

    @staticmethod
    async def disable_user(user_id: UUID) -> Optional[User]:
        return await UserService.update_user(user_id, UserUpdate(disabled=True))

    @staticmethod
    async def enable_user(user_id: UUID) -> Optional[User]:
        return await UserService.update_user(user_id, UserUpdate(disabled=False))