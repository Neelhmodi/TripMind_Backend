import os
import logging
from dotenv import load_dotenv
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# Load environment variables from backend/.env using absolute path
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
load_dotenv(dotenv_path)

# Fetch configuration
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.environ.get("MONGODB_DB", "tripmind")

logger.info("Connecting to MongoDB at: %s", MONGODB_URI)

try:
    # Initialize MongoClient with a 5-second server selection timeout
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    # Trigger a ping to verify if server is alive
    client.admin.command('ping')
    logger.info("Successfully connected to MongoDB database: %s", MONGODB_DB)
except Exception as e:
    logger.error("CRITICAL: Failed to connect to MongoDB! Please verify it is running. Error: %s", e)
    # Fallback/dummy client logic is not strictly needed as uvicorn/fastapi reload will retry,
    # but we let it proceed to allow developers to see startup logs.

db = client[MONGODB_DB]
users_collection = db["users"]

# Verify/Create unique index on email to enforce uniqueness at the database layer
try:
    users_collection.create_index("email", unique=True)
    logger.info("Unique index on users 'email' verified/created successfully.")
except Exception as e:
    logger.error("Failed to verify/create unique index on users 'email': %s", e)
