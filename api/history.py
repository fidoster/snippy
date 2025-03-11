from flask import Blueprint, request, jsonify, send_file
import json
import logging
import asyncio
import os
import csv
from io import StringIO
from tempfile import NamedTemporaryFile
from lib.blob_storage import get_search_history, get_search_results, delete_blob, put_blob

# Configure logger
logger = logging.getLogger(__name__)

history_bp = Blueprint('history', __name__, url_prefix='/api/history')

@history_bp.route('', methods=['GET'])
def get_history():
    """Get search history"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            history = loop.run_until_complete(get_search_history())
            
            return jsonify({
                "status": "success",
                "history": history
            })
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        return jsonify({"error": str(e)}), 500

@history_bp.route('/<path:search_id>', methods=['GET'])
def get_history_results(search_id):
    """Get search results from history"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(get_search_results(search_id))
            
            if not results:
                return jsonify({"error": "Search not found"}), 404
                
            return jsonify({
                "status": "success",
                "results": results
            })
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Error getting history results: {str(e)}")
        return jsonify({"error": str(e)}), 500

@history_bp.route('/<path:search_id>', methods=['DELETE'])
def delete_search(search_id):
    """Delete a search from history"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Delete the search
            success = loop.run_until_complete(delete_blob(search_id))
            
            if not success:
                return jsonify({"error": "Failed to delete search"}), 500
                
            # Also update the search index
            history = loop.run_until_complete(get_search_history())
            updated_history = [h for h in history if h.get('id') != search_id]
            
            # Save updated index
            loop.run_until_complete(put_blob("search_index", {"searches": updated_history}))
            
            return jsonify({"status": "success"})
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Error deleting search: {str(e)}")
        return jsonify({"error": str(e)}), 500

@history_bp.route('/<path:search_id>/download', methods=['GET'])
def download_csv(search_id):
    """Download search results as CSV"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(get_search_results(search_id))
            
            if not results:
                return jsonify({"error": "Search not found"}), 404
                
            # Create CSV without pandas
            with NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
                # Get all possible field names
                fieldnames = set()
                for result in results:
                    fieldnames.update(result.keys())
                
                # Write CSV
                writer = csv.DictWriter(temp_file, fieldnames=sorted(fieldnames))
                writer.writeheader()
                for result in results:
                    writer.writerow(result)
                
                temp_filename = temp_file.name
                
            # Send the file
            return send_file(
                temp_filename,
                as_attachment=True,
                download_name=f"{search_id.split('/')[-1]}_results.csv",
                mimetype='text/csv'
            )
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Error downloading CSV: {str(e)}")
        return jsonify({"error": str(e)}), 500