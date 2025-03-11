import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import time
from .api_utils import crossref_search, get_jufo_level

# Configure logger
logger = logging.getLogger(__name__)

async def search(query: str, offset: int = 0, limit: int = 10, year_range: str = "all") -> List[Dict[str, Any]]:
    """
    Search for academic articles
    
    Args:
        query: Search query
        offset: Pagination offset
        limit: Number of results to return
        year_range: Year range filter ("all", "2010-9999", "2015-9999", "2020-9999", or "custom")
        
    Returns:
        List of article information
    """
    try:
        # Process year range filter
        year_start = None
        year_end = None
        
        if year_range != "all":
            parts = year_range.split("-")
            if len(parts) == 2:
                try:
                    year_start = int(parts[0])
                    year_end = int(parts[1]) if parts[1] != "9999" else None
                except ValueError:
                    pass
        
        # Search Crossref
        results = await crossref_search(query, rows=limit, offset=offset)
        
        # Filter by year if specified
        if year_start is not None:
            filtered_results = []
            for item in results:
                year_str = item.get("year", "")
                try:
                    year = int(year_str)
                    if year >= year_start and (year_end is None or year <= year_end):
                        filtered_results.append(item)
                except ValueError:
                    # Skip items with invalid years
                    pass
            results = filtered_results
        
        return results
        
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        return []

async def enrich_with_jufo_levels(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich search results with JUFO levels
    
    Args:
        results: Search results
        
    Returns:
        Enriched search results
    """
    enriched_results = []
    
    for item in results:
        journal = item.get("journal", "Unknown")
        
        # Get JUFO level
        level = await get_jufo_level(journal)
        
        # Add level to item
        item["level"] = level
        
        enriched_results.append(item)
    
    return enriched_results

async def process_search_batch(
    query: str, 
    offset: int = 0, 
    limit: int = 20, 
    year_range: str = "all", 
    target_jufo: Optional[int] = None
) -> Tuple[List[Dict[str, Any]], bool, int]:
    """
    Process a batch of search results, enriching with JUFO levels
    
    Args:
        query: Search query
        offset: Pagination offset
        limit: Number of results to return
        year_range: Year range filter
        target_jufo: Target number of JUFO 2/3 articles to find
        
    Returns:
        Tuple of (enriched results, has more flag, JUFO 2/3 count)
    """
    try:
        # Search for articles
        results = await search(query, offset, limit, year_range)
        
        if not results:
            return [], False, 0
        
        # Enrich with JUFO levels
        enriched_results = await enrich_with_jufo_levels(results)
        
        # Count JUFO 2/3 articles
        jufo_count = sum(1 for r in enriched_results if r.get("level") in [2, 3])
        
        # Check if we have more results to fetch
        has_more = len(results) == limit
        
        # Check if we've reached the target JUFO count
        if target_jufo is not None and jufo_count >= target_jufo:
            has_more = False
        
        return enriched_results, has_more, jufo_count
        
    except Exception as e:
        logger.error(f"Error in process_search_batch: {str(e)}")
        return [], False, 0

async def sort_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort search results by JUFO level, then year
    
    Args:
        results: Search results
        
    Returns:
        Sorted search results
    """
    # Assign sort keys
    def get_sort_key(item):
        level = item.get("level")
        level_key = -1 if level is None else -int(level)  # Highest level first
        year_str = item.get("year", "0")
        year = int(year_str) if year_str.isdigit() else 0
        return (level_key, -year)  # Most recent year first
    
    return sorted(results, key=get_sort_key)