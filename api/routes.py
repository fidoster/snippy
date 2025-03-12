from flask import Blueprint, request, jsonify, render_template

# Configure logger
import logging
logger = logging.getLogger(__name__)

# Create Blueprint - CHANGED NAME TO AVOID CONFLICT
api_routes_bp = Blueprint('api_routes', __name__)

@api_routes_bp.route('/', methods=['GET'])
def index():
    """Render the main search page"""
    try:
        # Log for debugging
        logger.info("Rendering index.html template")
        return render_template('index.html', from_history=False)
    except Exception as e:
        # Log detailed error
        logger.error(f"Error rendering template: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to render template",
            "error": str(e)
        })

@api_routes_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok", 
        "message": "Snippy API is healthy",
        "version": "1.0.0"
    })