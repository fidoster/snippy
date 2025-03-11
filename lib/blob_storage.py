import os
import json
import time
import uuid
import logging
import httpx
from typing import Dict, List, Any, Optional, Union

# Configure logger
logger = logging.getLogger(__name__)

# Constants
VERCEL_BLOB_API_URL = "https://blob.vercel-storage.com"
VERCEL_BLOB_STORE_ID = os.environ.get("BLOB_STORE_ID")
VERCEL_BLOB_READ_WRITE_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN")
EDGE_CONFIG_ID = os.environ.get("EDGE_CONFIG_ID")
EDGE_CONFIG_TOKEN = os.environ.get("EDGE_CONFIG_TOKEN")

# Check if running in development mode
IS_DEVELOPMENT = not os.environ.get("VERCEL")

# For local development, use a simple file-based storage in /tmp
LOCAL_STORAGE_DIR = os.path.join('/tmp', "local_storage")
os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

async def put_blob(key: str, data: Union[str, dict, bytes], content_type: str = "application/json") -> Optional[str]:
    """Store data in Vercel Blob"""
    try:
        if IS_DEVELOPMENT:
            # Local storage for development
            filename = os.path.join(LOCAL_STORAGE_DIR, f"{key.replace('/', '_')}.json")
            
            # Convert data to string if it's a dictionary
            if isinstance(data, dict):
                data = json.dumps(data)
            elif isinstance(data, bytes):
                data = data.decode('utf-8')
                
            with open(filename, 'w') as f:
                f.write(data)
            return f"file://{filename}"
        
        # Prepare data for Vercel Blob
        if isinstance(data, dict):
            data = json.dumps(data).encode('utf-8')
        elif isinstance(data, str):
            data = data.encode('utf-8')
        
        # Upload to Vercel Blob
        async with httpx.AsyncClient() as client:
            # Step 1: Get a presigned URL for upload
            response = await client.post(
                f"{VERCEL_BLOB_API_URL}",
                headers={
                    "Authorization": f"Bearer {VERCEL_BLOB_READ_WRITE_TOKEN}",
                    "X-Vercel-Blob-Store-Id": VERCEL_BLOB_STORE_ID
                },
                json={
                    "contentType": content_type,
                    "pathname": key
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get presigned URL: {response.text}")
                return None
                
            presigned_data = response.json()
            upload_url = presigned_data.get('url')
            
            # Step 2: Upload the data
            upload_response = await client.put(
                upload_url,
                content=data,
                headers={"Content-Type": content_type}
            )
            
            if upload_response.status_code != 200:
                logger.error(f"Failed to upload blob: {upload_response.text}")
                return None
                
            return presigned_data.get('url')
            
    except Exception as e:
        logger.error(f"Error storing blob {key}: {str(e)}")
        return None

async def get_blob(key: str) -> Optional[Union[dict, str]]:
    """Retrieve data from Vercel Blob"""
    try:
        if IS_DEVELOPMENT:
            # Local storage for development
            filename = os.path.join(LOCAL_STORAGE_DIR, f"{key.replace('/', '_')}.json")
            if not os.path.exists(filename):
                return None
                
            with open(filename, 'r') as f:
                content = f.read()
                
            try:
                # Try to parse as JSON
                return json.loads(content)
            except json.JSONDecodeError:
                # Return as string if not valid JSON
                return content
        
        # Retrieve from Vercel Blob
        blob_url = f"{VERCEL_BLOB_API_URL}/{VERCEL_BLOB_STORE_ID}/{key}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                blob_url,
                headers={
                    "Authorization": f"Bearer {VERCEL_BLOB_READ_WRITE_TOKEN}"
                }
            )
            
            if response.status_code != 200:
                if response.status_code == 404:
                    return None
                logger.error(f"Failed to retrieve blob: {response.text}")
                return None
                
            # Try to parse as JSON
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
                
    except Exception as e:
        logger.error(f"Error retrieving blob {key}: {str(e)}")
        return None

async def delete_blob(key: str) -> bool:
    """Delete data from Vercel Blob"""
    try:
        if IS_DEVELOPMENT:
            # Local storage for development
            filename = os.path.join(LOCAL_STORAGE_DIR, f"{key.replace('/', '_')}.json")
            if os.path.exists(filename):
                os.remove(filename)
            return True
        
        # Delete from Vercel Blob
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{VERCEL_BLOB_API_URL}/{VERCEL_BLOB_STORE_ID}/{key}",
                headers={
                    "Authorization": f"Bearer {VERCEL_BLOB_READ_WRITE_TOKEN}"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to delete blob: {response.text}")
                return False
                
            return True
            
    except Exception as e:
        logger.error(f"Error deleting blob {key}: {str(e)}")
        return False

async def list_blobs(prefix: str = "") -> List[Dict[str, Any]]:
    """List blobs with the given prefix"""
    try:
        if IS_DEVELOPMENT:
            # Local storage for development
            results = []
            for filename in os.listdir(LOCAL_STORAGE_DIR):
                if filename.startswith(prefix.replace('/', '_')):
                    path = filename.replace('_', '/').replace('.json', '')
                    file_path = os.path.join(LOCAL_STORAGE_DIR, filename)
                    stats = os.stat(file_path)
                    results.append({
                        "pathname": path,
                        "size": stats.st_size,
                        "uploadedAt": stats.st_mtime
                    })
            return results
        
        # List from Vercel Blob
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{VERCEL_BLOB_API_URL}/list",
                headers={
                    "Authorization": f"Bearer {VERCEL_BLOB_READ_WRITE_TOKEN}",
                    "X-Vercel-Blob-Store-Id": VERCEL_BLOB_STORE_ID
                },
                params={"prefix": prefix}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to list blobs: {response.text}")
                return []
                
            data = response.json()
            return data.get("blobs", [])
            
    except Exception as e:
        logger.error(f"Error listing blobs with prefix {prefix}: {str(e)}")
        return []

# Helper functions for storing common data types
async def save_search_results(keywords: str, results: List[Dict[str, Any]]) -> bool:
    """Save search results to Blob storage"""
    timestamp = time.strftime("%Y%m%d%H%M%S")
    key = f"searches/{keywords.replace(' ', '_')}_{timestamp}"
    data = {
        "keywords": keywords,
        "timestamp": timestamp,
        "results": results,
        "count": len(results)
    }
    
    # Store the data
    url = await put_blob(key, data)
    
    if url:
        # Update the search index
        await update_search_index(key, {
            "id": key,
            "keywords": keywords,
            "timestamp": timestamp,
            "count": len(results)
        })
        return True
    return False

async def get_search_history() -> List[Dict[str, Any]]:
    """Get search history from Blob storage"""
    index = await get_blob("search_index") or {"searches": []}
    return sorted(index.get("searches", []), key=lambda x: x.get("timestamp", ""), reverse=True)

async def get_search_results(search_id: str) -> List[Dict[str, Any]]:
    """Get search results by ID"""
    data = await get_blob(search_id)
    if data and isinstance(data, dict):
        return data.get("results", [])
    return []

async def update_search_index(search_id: str, metadata: Dict[str, Any]):
    """Update the search index with new search metadata"""
    # Get current index
    index = await get_blob("search_index") or {"searches": []}
    
    # Add new entry
    index["searches"].append(metadata)
    
    # Save updated index
    await put_blob("search_index", index)

# Edge Config Functions
async def get_edge_config_item(key: str) -> Optional[Any]:
    """Get an item from Edge Config"""
    try:
        if IS_DEVELOPMENT:
            # Check local file
            filename = os.path.join(LOCAL_STORAGE_DIR, "edge_config.json")
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    config = json.load(f)
                    return config.get(key)
            return None
        
        # Get from Edge Config
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://edge-config.vercel.com/items/{key}",
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
    """Set an item in Edge Config"""
    try:
        if IS_DEVELOPMENT:
            # Save to local file
            filename = os.path.join(LOCAL_STORAGE_DIR, "edge_config.json")
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
                
            config[key] = value
            
            with open(filename, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        
        # Set in Edge Config
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://edge-config.vercel.com/items",
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

# JUFO-specific functions
async def get_jufo_level(journal_name: str) -> Optional[int]:
    """Get JUFO level for a journal from Edge Config cache"""
    if not journal_name or journal_name == "Unknown":
        return None
        
    # Get from Edge Config
    jufo_cache = await get_edge_config_item("jufo_cache") or {}
    return jufo_cache.get(journal_name)

async def set_jufo_level(journal_name: str, level: Optional[int]) -> bool:
    """Set JUFO level for a journal in Edge Config cache"""
    if not journal_name or journal_name == "Unknown":
        return False
        
    # Get current cache
    jufo_cache = await get_edge_config_item("jufo_cache") or {}
    
    # Update cache
    jufo_cache[journal_name] = level
    
    # Save updated cache
    return await set_edge_config_item("jufo_cache", jufo_cache)

# Project-related functions
async def save_project(project_data: Dict[str, Any]) -> Optional[str]:
    """
    Save a project to blob storage
    
    Args:
        project_data: Project data to save
        
    Returns:
        Project ID if successful, None otherwise
    """
    project_id = project_data.get('id') or str(uuid.uuid4())
    project_data['id'] = project_id
    
    # Store the project
    key = f"projects/{project_id}"
    url = await put_blob(key, project_data)
    
    if url:
        return project_id
    return None

async def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a project by ID
    
    Args:
        project_id: Project ID
        
    Returns:
        Project data if found, None otherwise
    """
    key = f"projects/{project_id}"
    return await get_blob(key)

async def get_all_projects() -> List[Dict[str, Any]]:
    """
    Get all projects
    
    Returns:
        List of projects
    """
    # List all project blobs
    blobs = await list_blobs(prefix="projects/")
    
    # Get each project
    projects = []
    for blob in blobs:
        path = blob.get("pathname")
        if path:
            project_id = path.split("/")[-1]
            project = await get_project(project_id)
            if project:
                projects.append(project)
    
    return projects

async def delete_project(project_id: str) -> bool:
    """
    Delete a project
    
    Args:
        project_id: Project ID
        
    Returns:
        True if successful, False otherwise
    """
    # Delete project
    key = f"projects/{project_id}"
    success = await delete_blob(key)
    
    # Also delete associated sections
    if success:
        sections_blobs = await list_blobs(prefix=f"sections/{project_id}/")
        for blob in sections_blobs:
            path = blob.get("pathname")
            if path:
                await delete_blob(path)
    
    return success

async def save_section(project_id: str, section_data: Dict[str, Any]) -> Optional[str]:
    """
    Save a section to a project
    
    Args:
        project_id: Project ID
        section_data: Section data to save
        
    Returns:
        Section ID if successful, None otherwise
    """
    section_id = section_data.get('id') or str(uuid.uuid4())
    section_data['id'] = section_id
    
    # Store the section
    key = f"sections/{project_id}/{section_id}"
    url = await put_blob(key, section_data)
    
    if url:
        return section_id
    return None

async def get_sections(project_id: str) -> List[Dict[str, Any]]:
    """
    Get all sections for a project
    
    Args:
        project_id: Project ID
        
    Returns:
        List of sections
    """
    # List all section blobs for this project
    blobs = await list_blobs(prefix=f"sections/{project_id}/")
    
    # Get each section
    sections = []
    for blob in blobs:
        path = blob.get("pathname")
        if path:
            section = await get_blob(path)
            if section:
                sections.append(section)
    
    return sections

async def delete_section(project_id: str, section_id: str) -> bool:
    """
    Delete a section
    
    Args:
        project_id: Project ID
        section_id: Section ID
        
    Returns:
        True if successful, False otherwise
    """
    key = f"sections/{project_id}/{section_id}"
    return await delete_blob(key)

async def save_article(project_id: str, section_id: str, article_data: Dict[str, Any]) -> Optional[str]:
    """
    Save an article to a section
    
    Args:
        project_id: Project ID
        section_id: Section ID
        article_data: Article data to save
        
    Returns:
        Article ID if successful, None otherwise
    """
    article_id = article_data.get('id') or str(uuid.uuid4())
    article_data['id'] = article_id
    
    # Get section
    section = await get_blob(f"sections/{project_id}/{section_id}")
    if not section:
        return None
    
    # Add article to section
    if 'articles' not in section:
        section['articles'] = []
    
    # Check if article exists
    for i, article in enumerate(section['articles']):
        if article.get('id') == article_id:
            # Update existing article
            section['articles'][i] = article_data
            break
    else:
        # Add new article
        section['articles'].append(article_data)
    
    # Save updated section
    key = f"sections/{project_id}/{section_id}"
    url = await put_blob(key, section)
    
    if url:
        return article_id
    return None

async def get_articles(project_id: str, section_id: str) -> List[Dict[str, Any]]:
    """
    Get all articles for a section
    
    Args:
        project_id: Project ID
        section_id: Section ID
        
    Returns:
        List of articles
    """
    # Get section
    section = await get_blob(f"sections/{project_id}/{section_id}")
    if not section:
        return []
    
    # Return articles
    return section.get('articles', [])

async def delete_article(project_id: str, section_id: str, article_id: str) -> bool:
    """
    Delete an article
    
    Args:
        project_id: Project ID
        section_id: Section ID
        article_id: Article ID
        
    Returns:
        True if successful, False otherwise
    """
    # Get section
    section = await get_blob(f"sections/{project_id}/{section_id}")
    if not section:
        return False
    
    # Remove article
    if 'articles' in section:
        section['articles'] = [a for a in section['articles'] if a.get('id') != article_id]
    
    # Save updated section
    key = f"sections/{project_id}/{section_id}"
    return await put_blob(key, section) is not None