import httpx
import logging
import json
from typing import List, Dict, Any, Optional
from fuzzywuzzy import fuzz
from .edge_config import get_jufo_level as get_cached_jufo_level, set_jufo_level

# Configure logger
logger = logging.getLogger(__name__)

async def crossref_search(query: str, rows: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Search Crossref API for academic articles
    
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
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, params=params)
            
            if response.status_code != 200:
                logger.error(f"Crossref request failed: {response.status_code} - {response.text}")
                return []
                
            data = response.json()
            items = data["message"]["items"]
            
            return [{
                "title": item.get("title", ["No title"])[0],
                "link": f"https://doi.org/{item['DOI']}" if "DOI" in item else "No link available",
                "journal": item.get("container-title", ["Unknown"])[0],
                "year": str(item.get("issued", {}).get("date-parts", [[""]])[0][0]) if item.get("issued", {}).get("date-parts", [[""]])[0][0] else "N/A",
                "raw_info": f"{', '.join(item.get('author', [{'given': '', 'family': ''}])[0].values())} - {item.get('container-title', [''])[0]}, {item.get('issued', {}).get('date-parts', [['']])[0][0]}"
            } for item in items] if items else []
            
    except Exception as e:
        logger.error(f"Error in Crossref search: {str(e)}")
        return []

async def fetch_jufo_api(url: str) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch data from JUFO API
    
    Args:
        url: JUFO API URL
        
    Returns:
        JUFO API response data if successful, None otherwise
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    return data
            
            logger.warning(f"JUFO API returned non-list or empty: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"JUFO API error: {str(e)}")
        return None

async def try_jufo_queries_in_sequence(query: str) -> Optional[List[Dict[str, Any]]]:
    """
    Try different query parameters to JUFO API in sequence
    
    Args:
        query: Query string
        
    Returns:
        JUFO API response data if successful, None otherwise
    """
    base_url = "https://jufo-rest.csc.fi/v1.1/etsi.php"
    query = query[:100] if len(query) > 100 else query
    
    for param in ["nimi", "nimi", "issn"]:
        if param == "nimi":
            # First try exact match
            url = f"{base_url}?{param}={httpx.utils.quote(query)}"
        else:
            # Then try wildcard search
            url = f"{base_url}?{param}={httpx.utils.quote(f'*{query}*')}"
            
        data = await fetch_jufo_api(url)
        if data:
            return data
            
    return None

async def augment_jufo_result(item: Dict[str, Any]) -> Optional[int]:
    """
    Get JUFO level for an item
    
    Args:
        item: JUFO item data
        
    Returns:
        JUFO level if available, None otherwise
    """
    if not item.get("Jufo_ID"):
        return None
        
    details_url = f"https://jufo-rest.csc.fi/v1.1/kanava/{item['Jufo_ID']}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(details_url, timeout=10)
            
            if response.status_code == 200:
                detail_json = response.json()
                if detail_json and len(detail_json) > 0:
                    raw_level = detail_json[0].get("Level", "")
                    return int(raw_level) if raw_level.isdigit() else None
                    
        return None
        
    except Exception as e:
        logger.error(f"Error augmenting JUFO result: {str(e)}")
        return None

async def get_jufo_level(journal_name: str) -> Optional[int]:
    """
    Get JUFO level for a journal
    
    Args:
        journal_name: Journal name
        
    Returns:
        JUFO level if available, None otherwise
    """
    if journal_name == "Unknown":
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
        await set_jufo_level(journal_name, None)
        return None
        
    # Find the best match
    best_match = max(results, key=lambda x: fuzz.ratio(x.get("Name", ""), journal_name), default=None)
    ratio = fuzz.ratio(best_match.get("Name", ""), journal_name) if best_match else 0
    
    logger.debug(f"JUFO match for {journal_name}: {best_match.get('Name', '') if best_match else 'None'}, Ratio: {ratio}")
    
    if best_match and ratio > 60:
        level = await augment_jufo_result(best_match)
        await set_jufo_level(journal_name, level)
        logger.debug(f"JUFO level assigned: {journal_name} -> {level}")
        return level
        
    # No good match found
    await set_jufo_level(journal_name, None)
    return None