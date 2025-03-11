from flask import Blueprint, request, jsonify, render_template, redirect, url_for
import logging
import asyncio
import os
from lib.blob_storage import (
    get_search_history, 
    get_search_results, 
    save_search_results, 
    delete_blob, 
    put_blob  # Added missing import
)

# Configure logger
logger = logging.getLogger(__name__)

# Create Blueprint
routes_bp = Blueprint('routes', __name__)

@routes_bp.route('/', methods=['GET'])
def index():
    """Render the main search page"""
    return render_template('index.html', from_history=False)

@routes_bp.route('/history', methods=['GET'])
def history():
    """Render the search history page"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get search history
        history_data = loop.run_until_complete(get_search_history())
        
        # Format timestamps
        for item in history_data:
            timestamp_str = item.get('timestamp', '')
            if timestamp_str:
                try:
                    # Format: YYYYMMDDHHMMSS to YYYY-MM-DD HH:MM:SS
                    formatted = f"{timestamp_str[:4]}-{timestamp_str[4:6]}-{timestamp_str[6:8]} {timestamp_str[8:10]}:{timestamp_str[10:12]}:{timestamp_str[12:14]}"
                    item['timestamp'] = formatted
                except Exception as e:
                    logger.error(f"Error formatting timestamp: {str(e)}")
        
        return render_template('history.html', searches=history_data)
        
    except Exception as e:
        logger.error(f"Error rendering history page: {str(e)}")
        return render_template('history.html', searches=[])

@routes_bp.route('/history/<path:keywords>', methods=['GET'])
def history_results(keywords):
    """Render the search results from history"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Find the search ID from history
        history_data = loop.run_until_complete(get_search_history())
        
        search_id = None
        for item in history_data:
            if item.get('keywords') == keywords:
                search_id = item.get('id')
                break
        
        if not search_id:
            return render_template('index.html', from_history=False, error="Search not found")
        
        # Get search results
        results = loop.run_until_complete(get_search_results(search_id))
        
        return render_template('index.html', from_history=True, results=results, keywords=keywords)
        
    except Exception as e:
        logger.error(f"Error rendering history results: {str(e)}")
        return render_template('index.html', from_history=False, error=str(e))

@routes_bp.route('/download/<path:keywords>', methods=['GET'])
def download_csv(keywords):
    """Redirect to API endpoint for CSV download"""
    # Use asyncio to run async functions
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Find the search ID from history
    history_data = loop.run_until_complete(get_search_history())
    
    search_id = None
    for item in history_data:
        if item.get('keywords') == keywords:
            search_id = item.get('id')
            break
    
    if not search_id:
        return redirect(url_for('routes.index'))
    
    # Redirect to the download API endpoint
    return redirect(url_for('history.download_csv', search_id=search_id))

@routes_bp.route('/history/delete', methods=['POST'])
def delete_from_history():
    """Delete a search from history"""
    try:
        data = request.get_json()
        if not data or 'keywords' not in data:
            return jsonify({"error": "No keywords provided"}), 400
            
        keywords = data.get('keywords')
        
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Find the search ID from history
        history_data = loop.run_until_complete(get_search_history())
        
        search_id = None
        for item in history_data:
            if item.get('keywords') == keywords:
                search_id = item.get('id')
                break
        
        if not search_id:
            return jsonify({"error": "Search not found"}), 404
        
        # Delete the search
        success = loop.run_until_complete(delete_blob(search_id))
        
        if not success:
            return jsonify({"error": "Failed to delete search"}), 500
            
        # Update the search index
        history_data = [h for h in history_data if h.get('keywords') != keywords]
        loop.run_until_complete(put_blob("search_index", {"searches": history_data}))
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error deleting from history: {str(e)}")
        return jsonify({"error": str(e)}), 500

@routes_bp.route('/history/delete_article', methods=['POST'])
def delete_article():
    """Delete an article from search results"""
    try:
        data = request.get_json()
        if not data or 'keywords' not in data or 'link' not in data:
            return jsonify({"error": "Missing required data"}), 400
            
        keywords = data.get('keywords')
        link = data.get('link')
        
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Find the search ID from history
        history_data = loop.run_until_complete(get_search_history())
        
        search_id = None
        for item in history_data:
            if item.get('keywords') == keywords:
                search_id = item.get('id')
                break
        
        if not search_id:
            return jsonify({"error": "Search not found"}), 404
        
        # Get search results
        results = loop.run_until_complete(get_search_results(search_id))
        
        # Remove the article
        updated_results = [r for r in results if r.get('link') != link]
        
        # Save updated results
        search_data = {
            "keywords": keywords,
            "timestamp": next((item.get('timestamp') for item in history_data if item.get('keywords') == keywords), ""),
            "results": updated_results,
            "count": len(updated_results)
        }
        
        loop.run_until_complete(put_blob(search_id, search_data))
        
        # Update the search index
        for item in history_data:
            if item.get('keywords') == keywords:
                item['count'] = len(updated_results)
                
        loop.run_until_complete(put_blob("search_index", {"searches": history_data}))
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error deleting article: {str(e)}")
        return jsonify({"error": str(e)}), 500

@routes_bp.route('/history/delete_non_jufo', methods=['POST'])
def delete_non_jufo():
    """Delete all non-JUFO ranked articles from search results"""
    try:
        data = request.get_json()
        if not data or 'keywords' not in data:
            return jsonify({"error": "No keywords provided"}), 400
            
        keywords = data.get('keywords')
        
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Find the search ID from history
        history_data = loop.run_until_complete(get_search_history())
        
        search_id = None
        for item in history_data:
            if item.get('keywords') == keywords:
                search_id = item.get('id')
                break
        
        if not search_id:
            return jsonify({"error": "Search not found"}), 404
        
        # Get search results
        results = loop.run_until_complete(get_search_results(search_id))
        
        # Keep only JUFO ranked articles
        updated_results = [r for r in results if r.get('level') is not None]
        
        # Save updated results
        search_data = {
            "keywords": keywords,
            "timestamp": next((item.get('timestamp') for item in history_data if item.get('keywords') == keywords), ""),
            "results": updated_results,
            "count": len(updated_results)
        }
        
        loop.run_until_complete(put_blob(search_id, search_data))
        
        # Update the search index
        for item in history_data:
            if item.get('keywords') == keywords:
                item['count'] = len(updated_results)
                
        loop.run_until_complete(put_blob("search_index", {"searches": history_data}))
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error deleting non-JUFO articles: {str(e)}")
        return jsonify({"error": str(e)}), 500