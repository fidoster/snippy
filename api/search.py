# api/search.py - Optimized version with shorter timeouts and better error handling

from flask import Blueprint, request, jsonify
import json
import logging
import asyncio
import httpx
from lib.search_logic import search, process_search_batch, sort_results
from lib.blob_storage import save_search_results, get_search_results, get_search_history

# Configure logger
logger = logging.getLogger(__name__)

search_bp = Blueprint('search', __name__, url_prefix='/api/search')

@search_bp.route('', methods=['POST'])
def start_search():
    """Start a search for articles with optimized performance for serverless"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        keywords = data.get('keywords')
        max_articles = min(int(data.get('max_articles', 100)), 100)  # Limit max articles to 100 initially
        target_jufo = int(data.get('target_jufo')) if data.get('target_jufo') else None
        year_range = data.get('year_range', 'all')
        
        if not keywords:
            return jsonify({"error": "Keywords are required"}), 400
            
        # Process smaller initial batch for faster response
        initial_batch_size = 10  # Reduced from 20
        
        # Use asyncio with a timeout
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Set a timeout for the entire operation
            batch_results, has_more, jufo_count = loop.run_until_complete(
                asyncio.wait_for(
                    process_search_batch(keywords, 0, initial_batch_size, year_range, target_jufo),
                    timeout=8.0  # 8 second timeout to allow for response processing
                )
            )
            
            # Save initial results asynchronously
            loop.run_until_complete(
                asyncio.wait_for(
                    save_search_results(keywords, batch_results),
                    timeout=1.0
                )
            )
            
            return jsonify({
                "status": "success",
                "initial_results": batch_results,
                "count": len(batch_results),
                "jufo_count": jufo_count,
                "has_more": has_more,
                "next_offset": initial_batch_size,
                "message": "First batch of results loaded. Continue fetching more."
            })
        except asyncio.TimeoutError:
            logger.warning(f"Search timed out for query: {keywords}")
            return jsonify({
                "status": "partial_success",
                "error": "The search is taking longer than expected. Try a more specific query.",
                "initial_results": [],
                "count": 0,
                "jufo_count": 0,
                "has_more": False
            }), 408  # Request Timeout status
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Error starting search: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e),
            "message": "An unexpected error occurred. Please try a simpler search query."
        }), 500

@search_bp.route('/more', methods=['POST'])
def get_more_results():
    """Get more search results with optimized performance for serverless"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        keywords = data.get('keywords')
        offset = int(data.get('offset', 0))
        batch_size = min(int(data.get('batch_size', 10)), 10)  # Smaller batch size
        year_range = data.get('year_range', 'all')
        target_jufo = data.get('target_jufo')
        
        if not keywords:
            return jsonify({"error": "Keywords are required"}), 400
            
        # Use asyncio with a timeout
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Get existing results with timeout
            search_key = f"searches/{keywords.replace(' ', '_')}"
            existing_results = loop.run_until_complete(
                asyncio.wait_for(
                    get_search_results(search_key),
                    timeout=3.0
                )
            )
            
            if existing_results is None:
                existing_results = []
                logger.warning(f"No existing results found for '{keywords}'")
            
            # Get next batch with timeout
            batch_results, has_more, batch_jufo_count = loop.run_until_complete(
                asyncio.wait_for(
                    process_search_batch(keywords, offset, batch_size, year_range, target_jufo),
                    timeout=5.0
                )
            )
            
            # Combine results, avoiding duplicates
            existing_links = {r.get('link') for r in existing_results if r.get('link')}
            unique_new_results = [r for r in batch_results if r.get('link') not in existing_links]
            
            combined_results = existing_results + unique_new_results
            
            # Count total JUFO 2/3 articles
            jufo_count = sum(1 for r in combined_results if r.get('level') in [2, 3])
            
            # Sort and save combined results with timeout
            sorted_results = loop.run_until_complete(
                asyncio.wait_for(
                    sort_results(combined_results),
                    timeout=1.0
                )
            )
            
            # Save results
            loop.run_until_complete(
                asyncio.wait_for(
                    save_search_results(keywords, sorted_results),
                    timeout=1.0
                )
            )
            
            return jsonify({
                "status": "success",
                "new_results": unique_new_results,
                "count": len(combined_results),
                "jufo_count": jufo_count,
                "has_more": has_more,
                "next_offset": offset + batch_size
            })
            
        except asyncio.TimeoutError:
            logger.warning(f"Search more timed out for query: {keywords} at offset {offset}")
            return jsonify({
                "status": "partial_timeout",
                "error": "The search is taking longer than expected. Try a more specific query.",
                "new_results": [],
                "count": len(existing_results) if existing_results else 0,
                "has_more": False
            }), 408  # Request Timeout status
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error getting more results: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e),
            "message": "An unexpected error occurred. Please try a simpler search query."
        }), 500

# Health check endpoint for debugging
@search_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with useful diagnostics"""
    try:
        # Simple test of async behavior
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Test blob storage with timeout
            history = loop.run_until_complete(
                asyncio.wait_for(
                    get_search_history(),
                    timeout=2.0
                )
            )
            history_count = len(history) if history else 0
            
            # Test external API connection with timeout
            external_api_test = False
            try:
                # Define an async function to test the external API
                async def test_crossref_api():
                    async with httpx.AsyncClient() as client:
                        response = await client.get("https://api.crossref.org/works?query=test&rows=1")
                        return response.status_code == 200
                
                # Run the test with a timeout
                external_api_test = loop.run_until_complete(
                    asyncio.wait_for(
                        test_crossref_api(),
                        timeout=3.0
                    )
                )
            except (asyncio.TimeoutError, Exception) as api_error:
                logger.warning(f"External API test failed: {str(api_error)}")
                external_api_test = False
                
            return jsonify({
                "status": "healthy",
                "message": "Search API is functioning correctly",
                "history_count": history_count,
                "blob_storage": "connected" if history is not None else "error",
                "external_api": "connected" if external_api_test else "error or timeout"
            })
        except asyncio.TimeoutError:
            return jsonify({
                "status": "partial",
                "message": "Search API health check timed out",
                "error": "Timeout during health check"
            }), 408
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500