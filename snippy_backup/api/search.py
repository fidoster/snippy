from flask import Blueprint, request, jsonify
import json
import logging
import asyncio
from lib.search_logic import search, process_search_batch, sort_results
from lib.blob_storage import save_search_results, get_search_results

# Configure logger
logger = logging.getLogger(__name__)

search_bp = Blueprint('search', __name__, url_prefix='/api/search')

@search_bp.route('', methods=['POST'])
def start_search():
    """Start a search for articles"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        keywords = data.get('keywords')
        max_articles = int(data.get('max_articles', 1000))
        target_jufo = int(data.get('target_jufo')) if data.get('target_jufo') else None
        year_range = data.get('year_range', 'all')
        
        if not keywords:
            return jsonify({"error": "Keywords are required"}), 400
            
        # Process initial batch (serverless functions have time limits)
        initial_batch_size = 20
        
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        batch_results, has_more, jufo_count = loop.run_until_complete(
            process_search_batch(keywords, 0, initial_batch_size, year_range, target_jufo)
        )
        
        # Save initial results
        loop.run_until_complete(save_search_results(keywords, batch_results))
        
        return jsonify({
            "status": "success",
            "initial_results": batch_results,
            "count": len(batch_results),
            "jufo_count": jufo_count,
            "has_more": has_more,
            "next_offset": initial_batch_size
        })
        
    except Exception as e:
        logger.error(f"Error starting search: {str(e)}")
        return jsonify({"error": str(e)}), 500

@search_bp.route('/more', methods=['POST'])
def get_more_results():
    """Get more search results"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        keywords = data.get('keywords')
        offset = int(data.get('offset', 0))
        batch_size = int(data.get('batch_size', 20))
        year_range = data.get('year_range', 'all')
        
        if not keywords:
            return jsonify({"error": "Keywords are required"}), 400
            
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get existing results
        existing_results = loop.run_until_complete(get_search_results(f"searches/{keywords.replace(' ', '_')}"))
        
        # Get next batch
        batch_results, has_more, batch_jufo_count = loop.run_until_complete(
            process_search_batch(keywords, offset, batch_size, year_range)
        )
        
        # Combine results, avoiding duplicates
        existing_links = {r.get('link') for r in existing_results}
        unique_new_results = [r for r in batch_results if r.get('link') not in existing_links]
        
        combined_results = existing_results + unique_new_results
        
        # Count total JUFO 2/3 articles
        jufo_count = sum(1 for r in combined_results if r.get('level') in [2, 3])
        
        # Sort and save combined results
        sorted_results = loop.run_until_complete(sort_results(combined_results))
        loop.run_until_complete(save_search_results(keywords, sorted_results))
        
        return jsonify({
            "status": "success",
            "new_results": unique_new_results,
            "count": len(combined_results),
            "jufo_count": jufo_count,
            "has_more": has_more,
            "next_offset": offset + batch_size
        })
        
    except Exception as e:
        logger.error(f"Error getting more results: {str(e)}")
        return jsonify({"error": str(e)}), 500

@search_bp.route('/results/<path:search_id>', methods=['GET'])
def get_search_results_endpoint(search_id):
    """Get search results by ID"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(get_search_results(search_id))
        
        if not results:
            return jsonify({"error": "Search not found"}), 404
            
        return jsonify({
            "status": "success", 
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Error retrieving search results: {str(e)}")
        return jsonify({"error": str(e)}), 500