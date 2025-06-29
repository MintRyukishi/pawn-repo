# backend/app/app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from app.core.config import settings
from app.models.user_model import User
from app.models.customer_model import Customer
from app.models.item_model import Item
from app.models.transaction_model import Transaction
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.api.api_v1.router import router

import logging
logging.getLogger("pymongo").setLevel(logging.WARNING)

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pawnrepo.log')
    ]
)

logger = logging.getLogger(__name__)

# Database connection globals
client = None
database = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan - startup and shutdown events
    """
    global client, database
    
    # Startup
    try:
        logger.info("Starting Pawn Repo application...")
        
        # Create MongoDB client and get database
        logger.info(f"Connecting to MongoDB...")
        client = AsyncIOMotorClient(settings.MONGO_CONNECTION_STRING)
        
        # Test the connection
        await client.admin.command('ping')
        logger.info("MongoDB connection successful")
        
        database = client.pawnrepo  # Database name
        
        # Initialize Beanie with your document models
        await init_beanie(
            database=database,
            document_models=[
                User,
                Customer,
                Item,
                Transaction
            ]
        )
        
        logger.info("Beanie ODM initialized successfully")
        logger.info(f"Application started successfully on {settings.PROJECT_NAME}")
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        if client:
            client.close()
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    if client:
        client.close()
        logger.info("Disconnected from MongoDB")

# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    debug=settings.DEBUG,
    description="Pawn Repo - Pawnshop Management System API",
    version="1.0.0"
)

# CORS configuration
origins = [
    "http://localhost:3000",    # React default port
    "http://localhost:8080",    # Vue default port  
    "http://localhost:5173",    # Vite default port
    "http://127.0.0.1:3000",    # Alternative localhost
    "http://127.0.0.1:8080",
    "http://127.0.0.1:5173"
]

# Add configured CORS origins
if settings.BACKEND_CORS_ORIGINS:
    origins.extend(settings.BACKEND_CORS_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        if client:
            await client.admin.command('ping')
            db_status = "connected"
        else:
            db_status = "disconnected"
        
        return {
            "status": "healthy",
            "database": db_status,
            "application": settings.PROJECT_NAME,
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Include API router
app.include_router(router, prefix=settings.API_V1_STR)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return HTTPException(
        status_code=500,
        detail="An unexpected error occurred. Please try again later."
    )