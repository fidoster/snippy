from flask import Flask, jsonify, request
import os
import logging
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Import just the core blueprints first
from api.search import search_bp
from api.history import history_bp

# Create Flask app for serverless
app = Flask(__name__, 
           static_folder='public',
           static_url_path='/static',
           template_folder='templates')

# Configure app
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['DEBUG'] = os.environ.get('FLASK_ENV', 'development') == 'development'

# Register just core blueprints first
app.register_blueprint(search_bp)
app.register_blueprint(history_bp)

# Register error handlers
@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    if request.path.startswith('/api/'):
        return jsonify({"error": "Not found"}), 404
    return jsonify({"error": "Page not found", "status": 404}), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    error_traceback = traceback.format_exc()
    logger.error(f"Server error: {str(e)}\n{error_traceback}")
    if request.path.startswith('/api/'):
        return jsonify({"error": "Internal server error"}), 500
    return jsonify({"error": "Internal server error", "status": 500}), 500

# Add template filter for parsing JSON strings
@app.template_filter('fromjson')
def from_json(value):
    import json
    return json.loads(value)

# Root route for health check
@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Snippy API is running"})

# For local development
if __name__ == '__main__':
    app.run(debug=True)