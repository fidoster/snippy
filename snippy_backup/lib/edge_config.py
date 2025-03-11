import os
import json
import logging
import httpx
from typing import Dict, List, Any, Optional, Union

# Configure logger
logger = logging.getLogger(__name__)

# Constants
EDGE_CONFIG_URL = "https://edge-config.vercel.com"
EDGE_CONFIG_ID = os.environ.get("EDGE_CONFIG_ID")
EDGE_CONFIG_TOKEN = os.environ.get("EDGE_CONFIG_TOKEN")

# Check if running in development mode
IS_DEVELOPMENT = not os.environ.get("VERCEL")

# For local development, use a simple file-based cache
LOCAL_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "local_edge_config.json")

def _get_local_cache() -> Dict[str, Any]:
    """Get local cache for development"""
    if os.path.exists(LOCAL_CACHE_FILE):
        try:
            with open(LOCAL_CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading local cache: {str(e)}")
    return {}

def _save_local_cache(data: Dict[str, Any]):
    """Save local cache for development"""
    try:
        with open(LOCAL_CACHE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving local cache: {str(e)}")

async def get_edge_config_item(key: str) -> Optional[Any]:
    """
    Get an item from Edge Config
    
    Args:
        key: Key to retrieve
        
    Returns:
        Value if found, None otherwise
    """
    try:
        if IS_DEVELOPMENT:
            # Use local cache for development
            cache = _get_local_cache()
            return cache.get(key)
        
        # Get from Edge Config
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{EDGE_CONFIG_URL}/items/{key}",
                headers={
                    "Authorization": f"Bearer {EDGE_CONFIG_TOKEN}",
                    "X-Edge-Config-Id": EDGE_CONFIG_ID
                }
            )
            
            if response.status_code != 200:
                if response.status_code == 404:
                    return None
                logger.error(f"Failed to get Edge Config item: {response.text}")
                return None
                
            data = response.json()
            return data.get("value")
            
    except Exception as e:
        logger.error(f"Error getting Edge Config item {key}: {str(e)}")
        return None

async def set_edge_config_item(key: str, value: Any) -> bool:
    """
    Set an item in Edge Config
    
    Args:
        key: Key to set
        value: Value to set
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if IS_DEVELOPMENT:
            # Use local cache for development
            cache = _get_local_cache()
            cache[key] = value
            _save_local_cache(cache)
            return True
        
        # Set in Edge Config
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{EDGE_CONFIG_URL}/items",
                headers={
                    "Authorization": f"Bearer {EDGE_CONFIG_TOKEN}",
                    "X-Edge-Config-Id": EDGE_CONFIG_ID,
                    "Content-Type": "application/json"
                },
                json={key: value}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to set Edge Config item: {response.text}")
                return False
                
            return True
            
    except Exception as e:
        logger.error(f"Error setting Edge Config item {key}: {str(e)}")
        return False

async def delete_edge_config_item(key: str) -> bool:
    """
    Delete an item from Edge Config
    
    Args:
        key: Key to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if IS_DEVELOPMENT:
            # Use local cache for development
            cache = _get_local_cache()
            if key in cache:
                del cache[key]
                _save_local_cache(cache)
            return True
        
        # Delete from Edge Config
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{EDGE_CONFIG_URL}/items/{key}",
                headers={
                    "Authorization": f"Bearer {EDGE_CONFIG_TOKEN}",
                    "X-Edge-Config-Id": EDGE_CONFIG_ID
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to delete Edge Config item: {response.text}")
                return False
                
            return True
            
    except Exception as e:
        logger.error(f"Error deleting Edge Config item {key}: {str(e)}")
        return False

async def get_all_edge_config() -> Dict[str, Any]:
    """
    Get all items from Edge Config
    
    Returns:
        Dictionary of all items
    """
    try:
        if IS_DEVELOPMENT:
            # Use local cache for development
            return _get_local_cache()
        
        # Get from Edge Config
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{EDGE_CONFIG_URL}/items",
                headers={
                    "Authorization": f"Bearer {EDGE_CONFIG_TOKEN}",
                    "X-Edge-Config-Id": EDGE_CONFIG_ID
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get all Edge Config items: {response.text}")
                return {}
                
            return response.json()
            
    except Exception as e:
        logger.error(f"Error getting all Edge Config items: {str(e)}")
        return {}

# JUFO-specific functions

async def get_jufo_level(journal_name: str) -> Optional[int]:
    """
    Get JUFO level for a journal from Edge Config cache
    
    Args:
        journal_name: Journal name
        
    Returns:
        JUFO level if found, None otherwise
    """
    if not journal_name or journal_name == "Unknown":
        return None
        
    # Get from Edge Config
    jufo_cache = await get_edge_config_item("jufo_cache") or {}
    return jufo_cache.get(journal_name)

async def set_jufo_level(journal_name: str, level: Optional[int]) -> bool:
    """
    Set JUFO level for a journal in Edge Config cache
    
    Args:
        journal_name: Journal name
        level: JUFO level
        
    Returns:
        True if successful, False otherwise
    """
    if not journal_name or journal_name == "Unknown":
        return False
        
    # Get current cache
    jufo_cache = await get_edge_config_item("jufo_cache") or {}
    
    # Update cache
    jufo_cache[journal_name] = level
    
    # Save updated cache
    return await set_edge_config_item("jufo_cache", jufo_cache)

async def get_app_config() -> Dict[str, Any]:
    """
    Get application configuration from Edge Config
    
    Returns:
        Application configuration
    """
    return await get_edge_config_item("app_config") or {}

async def set_app_config(config: Dict[str, Any]) -> bool:
    """
    Set application configuration in Edge Config
    
    Args:
        config: Application configuration
        
    Returns:
        True if successful, False otherwise
    """
    return await set_edge_config_item("app_config", config)