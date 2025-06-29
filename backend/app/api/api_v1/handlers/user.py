# backend/app/api/api_v1/handlers/user.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from app.schemas.user_schema import UserAuth, UserOut, UserUpdate
from app.services.user_service import UserService
from app.api.deps.user_deps import get_current_user
from app.models.user_model import User
import pymongo
import logging

logger = logging.getLogger(__name__)
user_router = APIRouter()

@user_router.post("/create", summary="Create a new user", response_model=UserOut)
async def create_user(data: UserAuth):
    try:
        return await UserService.create_user(data)
    except pymongo.errors.DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="User with this email or username already exists."
        )
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

@user_router.get("/me", summary="Get current user", response_model=UserOut)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@user_router.get("/", summary="Get all users", response_model=List[UserOut])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    try:
        users = await UserService.get_all_users(skip=skip, limit=limit)
        return users
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users"
        )

@user_router.get("/{user_id}", summary="Get user by ID", response_model=UserOut)
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    try:
        user = await UserService.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user"
        )