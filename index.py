from flask import Flask, jsonify, request, render_template
import os
import logging
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Import all necessary blueprints
from api.search import search_bp
from api.history import history_bp
from api.index import routes_bp
from api.projects import projects_bp, projects_ui_bp  # Add projects_ui_bp import

# Create Flask app for serverless
app = Flask(__name__, 
           static_folder='public',
           static_url_path='/static',
           template_folder='templates')

# Configure app
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['DEBUG'] = os.environ.get('FLASK_ENV', 'development') == 'development'

# Register all blueprints
app.register_blueprint(search_bp)
app.register_blueprint(history_bp)
app.register_blueprint(routes_bp)
app.register_blueprint(projects_bp)
app.register_blueprint(projects_ui_bp)  # Register projects_ui_bp

# Register error handlers
@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    if request.path.startswith('/api/'):
        return jsonify({"error": "Not found"}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    error_traceback = traceback.format_exc()
    logger.error(f"Server error: {str(e)}\n{error_traceback}")
    if request.path.startswith('/api/'):
        return jsonify({"error": "Internal server error"}), 500
    return render_template('500.html'), 500

# Add template filter for parsing JSON strings
@app.template_filter('fromjson')
def from_json(value):
    import json
    return json.loads(value)

if __name__ == '__main__':
    app.run(debug=True)