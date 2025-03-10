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
LOCAL_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "local_storage")
os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

async def put_blob(key: str, data: Union[str, dict, bytes], content_type: str = "application/json") -> Optional[str]:
    """
    Store data in Vercel Blob
    
    Args:
        key: Unique identifier for the data
        data: Data to store (string, dict, or bytes)
        content_type: Content type of the data
        
    Returns:
        URL of the stored blob if successful, None otherwise
    """
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
    """
    Retrieve data from Vercel Blob
    
    Args:
        key: Unique identifier for the data
        
    Returns:
        Retrieved data (as dictionary if JSON, or string otherwise)
    """
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
    """
    Delete data from Vercel Blob
    
    Args:
        key: Unique identifier for the data
        
    Returns:
        True if deletion was successful, False otherwise
    """
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
    """
    List blobs with the given prefix
    
    Args:
        prefix: Prefix to filter blobs
        
    Returns:
        List of blob metadata
    """
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
    """
    Save search results to Blob storage
    
    Args:
        keywords: Search keywords
        results: Search results
        
    Returns:
        True if successful, False otherwise
    """
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
    """
    Get search history from Blob storage
    
    Returns:
        List of search history entries
    """
    index = await get_blob("search_index") or {"searches": []}
    return sorted(index.get("searches", []), key=lambda x: x.get("timestamp", ""), reverse=True)

async def get_search_results(search_id: str) -> List[Dict[str, Any]]:
    """
    Get search results by ID
    
    Args:
        search_id: Search ID
        
    Returns:
        Search results
    """
    data = await get_blob(search_id)
    if data and isinstance(data, dict):
        return data.get("results", [])
    return []

async def update_search_index(search_id: str, metadata: Dict[str, Any]):
    """
    Update the search index with new search metadata
    
    Args:
        search_id: Search ID
        metadata: Search metadata
    """
    # Get current index
    index = await get_blob("search_index") or {"searches": []}
    
    # Add new entry
    index["searches"].append(metadata)
    
    # Save updated index
    await put_blob("search_index", index)

# Project-related functions

async def save_project(project_data: Dict[str, Any]) -> Optional[str]:
    """
    Save a project to Blob storage
    
    Args:
        project_data: Project data
        
    Returns:
        Project ID if successful, None otherwise
    """
    project_id = project_data.get("id") or str(uuid.uuid4())
    project_data["id"] = project_id
    
    # Save project data
    key = f"projects/{project_id}"
    url = await put_blob(key, project_data)
    
    if url:
        # Update project index
        await update_project_index(project_id, {
            "id": project_id,
            "title": project_data.get("title", "Untitled Project"),
            "description": project_data.get("description", ""),
            "created_at": project_data.get("created_at", time.strftime("%Y-%m-%d %H:%M:%S"))
        })
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
    return await get_blob(f"projects/{project_id}")

async def get_all_projects() -> List[Dict[str, Any]]:
    """
    Get all projects
    
    Returns:
        List of project metadata
    """
    index = await get_blob("project_index") or {"projects": []}
    return sorted(index.get("projects", []), key=lambda x: x.get("created_at", ""), reverse=True)

async def delete_project(project_id: str) -> bool:
    """
    Delete a project
    
    Args:
        project_id: Project ID
        
    Returns:
        True if successful, False otherwise
    """
    # Delete project data
    success = await delete_blob(f"projects/{project_id}")
    
    if success:
        # Update project index
        index = await get_blob("project_index") or {"projects": []}
        index["projects"] = [p for p in index["projects"] if p.get("id") != project_id]
        await put_blob("project_index", index)
        
        # List and delete related sections
        sections = await list_blobs(f"sections/{project_id}/")
        for section in sections:
            await delete_blob(section["pathname"])
            
        return True
    return False

async def update_project_index(project_id: str, metadata: Dict[str, Any]):
    """
    Update the project index with new project metadata
    
    Args:
        project_id: Project ID
        metadata: Project metadata
    """
    # Get current index
    index = await get_blob("project_index") or {"projects": []}
    
    # Update or add entry
    existing = [i for i, p in enumerate(index["projects"]) if p.get("id") == project_id]
    if existing:
        index["projects"][existing[0]] = metadata
    else:
        index["projects"].append(metadata)
    
    # Save updated index
    await put_blob("project_index", index)

# Section-related functions

async def save_section(project_id: str, section_data: Dict[str, Any]) -> Optional[str]:
    """
    Save a section to Blob storage
    
    Args:
        project_id: Project ID
        section_data: Section data
        
    Returns:
        Section ID if successful, None otherwise
    """
    section_id = section_data.get("id") or str(uuid.uuid4())
    section_data["id"] = section_id
    section_data["project_id"] = project_id
    
    # Save section data
    key = f"sections/{project_id}/{section_id}"
    url = await put_blob(key, section_data)
    
    return section_id if url else None

async def get_sections(project_id: str) -> List[Dict[str, Any]]:
    """
    Get all sections for a project
    
    Args:
        project_id: Project ID
        
    Returns:
        List of section data
    """
    # List blobs with the section prefix
    blobs = await list_blobs(f"sections/{project_id}/")
    
    # Get each section's data
    sections = []
    for blob in blobs:
        data = await get_blob(blob["pathname"])
        if data:
            sections.append(data)
    
    return sorted(sections, key=lambda x: x.get("created_at", ""))

async def delete_section(project_id: str, section_id: str) -> bool:
    """
    Delete a section
    
    Args:
        project_id: Project ID
        section_id: Section ID
        
    Returns:
        True if successful, False otherwise
    """
    return await delete_blob(f"sections/{project_id}/{section_id}")

# Article-related functions

async def save_article(project_id: str, section_id: str, article_data: Dict[str, Any]) -> Optional[str]:
    """
    Save an article to Blob storage
    
    Args:
        project_id: Project ID
        section_id: Section ID
        article_data: Article data
        
    Returns:
        Article ID if successful, None otherwise
    """
    article_id = article_data.get("id") or str(uuid.uuid4())
    article_data["id"] = article_id
    
    # Save article data
    key = f"articles/{project_id}/{section_id}/{article_id}"
    url = await put_blob(key, article_data)
    
    return article_id if url else None

async def get_articles(project_id: str, section_id: str) -> List[Dict[str, Any]]:
    """
    Get all articles for a section
    
    Args:
        project_id: Project ID
        section_id: Section ID
        
    Returns:
        List of article data
    """
    # List blobs with the article prefix
    blobs = await list_blobs(f"articles/{project_id}/{section_id}/")
    
    # Get each article's data
    articles = []
    for blob in blobs:
        data = await get_blob(blob["pathname"])
        if data:
            articles.append(data)
    
    return sorted(articles, key=lambda x: x.get("added_at", ""))

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
    return await delete_blob(f"articles/{project_id}/{section_id}/{article_id}")