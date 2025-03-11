from flask import Blueprint, request, jsonify, render_template

# Configure logger
import logging
logger = logging.getLogger(__name__)

# Create Blueprint - NOTE: No url_prefix means routes start at /
routes_bp = Blueprint('routes', __name__)

@routes_bp.route('/', methods=['GET'])
def index():
    """Render the main search page"""
    try:
        # First try rendering template
        return render_template('index.html', from_history=False)
    except Exception as e:
        # Fall back to JSON response if template rendering fails
        logger.error(f"Error rendering template: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to render template",
            "error": str(e)
        })

@routes_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok", 
        "message": "Snippy API is healthy",
        "version": "1.0.0"
    })