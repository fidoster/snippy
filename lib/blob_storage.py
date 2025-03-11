import os
import json
import time
import uuid
import logging
from typing import Dict, List, Any, Optional, Union
import httpx

# Configure logger
logger = logging.getLogger(__name__)

# Constants
VERCEL_BLOB_API_URL = "https://blob.vercel-storage.com"
VERCEL_BLOB_STORE_ID = os.environ.get("BLOB_STORE_ID")
VERCEL_BLOB_READ_WRITE_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN")

# Check if running in development mode
IS_DEVELOPMENT = not os.environ.get("VERCEL")

# For local development, use a simple file-based storage
# CHANGE THIS LINE to use /tmp for Vercel
LOCAL_STORAGE_DIR = os.path.join('/tmp' if os.environ.get("VERCEL") else os.path.dirname(os.path.dirname(__file__)), "local_storage")
os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

# Rest of the file remains the same...