import httpx
import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from fuzzywuzzy import fuzz
from .edge_config import get_jufo_level as get_cached_jufo_level, set_jufo_level
from urllib.parse import quote  # Add this import for URL encoding

# Configure logger
logger = logging.getLogger(__name__)

async def crossref_search(query: str, rows: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Search Crossref API for academic articles with improved timeout handling
    
    Args:
        query: Search query
        rows: Number of results to return
        offset: Offset for pagination
        
    Returns:
        List of article information
    """
    base_url = "https://api.crossref.org/works"
    params = {
        "query": query, 
        "rows": rows, 
        "offset": offset, 
        "select": "DOI,title,container-title,issued"
    }
    
    try:
        # Create a client with a shorter timeout
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(base_url, params=params)
            
            if response.status_code != 200:
                logger.error(f"Crossref request failed: {response.status_code} - {response.text}")
                return []
                
            data = response.json()
            items = data.get("message", {}).get("items", [])
            
            results = []
            for item in items:
                try:
                    title = item.get("title", ["No title"])[0] if item.get("title") else "No title"
                    doi = item.get("DOI", "")
                    link = f"https://doi.org/{doi}" if doi else "No link available"
                    journal = item.get("container-title", ["Unknown"])[0] if item.get("container-title") else "Unknown"
                    
                    # Handle year data more safely
                    year = "N/A"
                    if item.get("issued") and item.get("issued").get("date-parts") and len(item.get("issued").get("date-parts")) > 0:
                        date_parts = item.get("issued").get("date-parts")[0]
                        if date_parts and len(date_parts) > 0 and date_parts[0]:
                            year = str(date_parts[0])
                    
                    # Get author information safely
                    author_info = ""
                    if item.get("author") and len(item.get("author")) > 0:
                        author = item.get("author")[0]
                        if isinstance(author, dict):
                            given = author.get("given", "")
                            family = author.get("family", "")
                            author_info = f"{family}, {given}" if family or given else ""
                    
                    raw_info = f"{author_info} - {journal}, {year}" if author_info else f"{journal}, {year}"
                    
                    results.append({
                        "title": title,
                        "link": link,
                        "journal": journal,
                        "year": year,
                        "raw_info": raw_info
                    })
                except Exception as item_error:
                    logger.warning(f"Error processing item: {str(item_error)}")
                    continue
            
            return results
            
    except httpx.ReadTimeout:
        logger.warning(f"Crossref search timed out for query: {query}")
        return []
    except Exception as e:
        logger.error(f"Error in Crossref search: {str(e)}")
        return []

async def fetch_jufo_api(url: str) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch data from JUFO API with shorter timeout
    
    Args:
        url: JUFO API URL
        
    Returns:
        JUFO API response data if successful, None otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    return data
            
            logger.warning(f"JUFO API returned non-list or empty: {response.status_code}")
            return None
            
    except httpx.ReadTimeout:
        logger.warning(f"JUFO API request timed out: {url}")
        return None
    except Exception as e:
        logger.error(f"JUFO API error: {str(e)}")
        return None

async def try_jufo_queries_in_sequence(query: str) -> Optional[List[Dict[str, Any]]]:
    """
    Try different query parameters to JUFO API in sequence, with early return
    
    Args:
        query: Query string
        
    Returns:
        JUFO API response data if successful, None otherwise
    """
    base_url = "https://jufo-rest.csc.fi/v1.1/etsi.php"
    
    # Truncate and sanitize query
    query = query[:100] if len(query) > 100 else query
    
    # First try exact name match (most likely to succeed quickly)
    url = f"{base_url}?nimi={quote(query)}"
    data = await fetch_jufo_api(url)
    if data:
        return data
    
    # Then try wildcard search if we have time
    url = f"{base_url}?nimi={quote(f'*{query}*')}"
    data = await fetch_jufo_api(url)
    if data:
        return data
    
    # Finally try ISSN if the query might be an ISSN
    if len(query) <= 9 and ('-' in query or query.isdigit()):
        url = f"{base_url}?issn={quote(query)}"
        data = await fetch_jufo_api(url)
        if data:
            return data
            
    return None

async def augment_jufo_result(item: Dict[str, Any]) -> Optional[int]:
    """
    Get JUFO level for an item with shorter timeout
    
    Args:
        item: JUFO item data
        
    Returns:
        JUFO level if available, None otherwise
    """
    if not item.get("Jufo_ID"):
        return None
        
    details_url = f"https://jufo-rest.csc.fi/v1.1/kanava/{item['Jufo_ID']}"
    
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(details_url)
            
            if response.status_code == 200:
                detail_json = response.json()
                if detail_json and len(detail_json) > 0:
                    raw_level = detail_json[0].get("Level", "")
                    return int(raw_level) if raw_level.isdigit() else None
                    
        return None
        
    except httpx.ReadTimeout:
        logger.warning(f"JUFO level lookup timed out for ID: {item['Jufo_ID']}")
        return None
    except Exception as e:
        logger.error(f"Error augmenting JUFO result: {str(e)}")
        return None

async def get_jufo_level(journal_name: str) -> Optional[int]:
    """
    Get JUFO level for a journal with improved caching
    
    Args:
        journal_name: Journal name
        
    Returns:
        JUFO level if available, None otherwise
    """
    if not journal_name or journal_name == "Unknown":
        return None
        
    # First, check the Edge Config cache
    cached_level = await get_cached_jufo_level(journal_name)
    if cached_level is not None:
        logger.debug(f"JUFO cache hit: {journal_name} -> {cached_level}")
        return cached_level
        
    # If not in cache, query the JUFO API
    results = await try_jufo_queries_in_sequence(journal_name)
    if not results:
        logger.debug(f"No JUFO results for: {journal_name}")
        # Cache the miss to avoid repeated queries for the same journal
        asyncio.create_task(set_jufo_level(journal_name, None))
        return None
        
    # Find the best match
    best_match = None
    best_ratio = 0
    
    for result in results:
        ratio = fuzz.ratio(result.get("Name", ""), journal_name)
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = result
    
    logger.debug(f"JUFO match for {journal_name}: {best_match.get('Name', '') if best_match else 'None'}, Ratio: {best_ratio}")
    
    if best_match and best_ratio > 60:
        level = await augment_jufo_result(best_match)
        # Cache the result asynchronously without waiting
        asyncio.create_task(set_jufo_level(journal_name, level))
        logger.debug(f"JUFO level assigned: {journal_name} -> {level}")
        return level
        
    # No good match found, cache the miss asynchronously
    asyncio.create_task(set_jufo_level(journal_name, None))
    return None