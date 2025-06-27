from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.models.user_model import User
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.api.api_v1.router import router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Database connection
client = None
database = None

# CORS configuration - good for development
origins = [
    "http://localhost:3000",    # React default port
    "http://localhost:8080",    # Vue default port  
    "http://localhost:5173",    # Vite default port
    "http://127.0.0.1:3000",    # Alternative localhost
    "http://127.0.0.1:8080",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def app_init():
    """
    Initialize crucial application services
    """
    global client, database
    
    # Create MongoDB client and get database
    client = AsyncIOMotorClient(settings.MONGO_CONNECTION_STRING)
    database = client.pawnrepo  # Database name
    
    # Initialize Beanie with your document models
    await init_beanie(
        database=database,
        document_models=[
            User
        ]  # Add your document models here
    )
    
    print("Connected to MongoDB and initialized Beanie")

@app.on_event("shutdown")
async def app_shutdown():
    """
    Clean up database connections
    """
    global client
    if client:
        client.close()
        print("Disconnected from MongoDB")

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

app.include_router(router, prefix=settings.API_V1_STR, tags=["api_v1"])