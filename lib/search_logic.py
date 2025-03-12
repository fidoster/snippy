import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import time
import httpx
from .api_utils import crossref_search, get_jufo_level

# Configure logger
logger = logging.getLogger(__name__)

async def search(query: str, offset: int = 0, limit: int = 10, year_range: str = "all") -> List[Dict[str, Any]]:
    """
    Search for academic articles with timeout handling
    
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
        
        # Search Crossref with timeout
        try:
            results = await asyncio.wait_for(
                crossref_search(query, rows=limit, offset=offset),
                timeout=6.0  # 6-second timeout for external API
            )
        except asyncio.TimeoutError:
            logger.warning(f"Crossref search timed out for query: {query}")
            return []
        
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
    Enrich search results with JUFO levels, with a limit on concurrent requests
    
    Args:
        results: Search results
        
    Returns:
        Enriched search results
    """
    enriched_results = []
    
    # Process in smaller batches to avoid overwhelming APIs
    batch_size = 5
    for i in range(0, len(results), batch_size):
        batch = results[i:i+batch_size]
        tasks = []
        
        for item in batch:
            journal = item.get("journal", "Unknown")
            
            # Create a task to get JUFO level with timeout
            async def get_level_with_timeout(journal_name):
                try:
                    return await asyncio.wait_for(
                        get_jufo_level(journal_name),
                        timeout=3.0  # 3-second timeout per journal
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"JUFO level lookup timed out for: {journal_name}")
                    return None
                    
            tasks.append(get_level_with_timeout(journal))
            
        # Wait for all tasks in this batch to complete
        try:
            levels = await asyncio.gather(*tasks)
            
            # Add levels to items
            for j, level in enumerate(levels):
                item = batch[j]
                item["level"] = level
                enriched_results.append(item)
                
        except Exception as e:
            logger.error(f"Error processing JUFO batch: {str(e)}")
            # Add items without levels
            for item in batch:
                item["level"] = None
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
    Process a batch of search results, enriching with JUFO levels, with better error handling
    
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