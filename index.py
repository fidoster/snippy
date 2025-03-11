from flask import Flask, jsonify, request
import os
import logging
from api.search import search_bp
from api.history import history_bp
from api.projects import projects_bp

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Create Flask app for serverless
app = Flask(__name__)

# Register blueprints
app.register_blueprint(search_bp)
app.register_blueprint(history_bp)
app.register_blueprint(projects_bp)

# Root route for health check
@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "version": "1.0.0"})

# Handle 404 errors
@app.errorhandler(404)
def not_found(e):
    logger.error(f"Not found: {request.path}")
    return jsonify({"error": "Not found"}), 404

# Handle 500 errors
@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500

# For local development
if __name__ == '__main__':
    app.run(debug=True)