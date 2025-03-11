from flask import Flask, render_template, jsonify, request
import os
import logging
from dotenv import load_dotenv

# Import API blueprints
from api.search import search_bp
from api.history import history_bp
from api.projects import projects_bp, projects_ui_bp
from api.index import routes_bp

# Load environment variables
load_dotenv()

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application"""
    app = Flask(
        __name__,
        static_folder='public',
        static_url_path='/static',
        template_folder='templates'
    )
    
    # Configure app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['DEBUG'] = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    # Register API blueprints - updated blueprint name
    app.register_blueprint(search_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(projects_bp)  # Now named 'projects_api'
    
    # Register UI blueprints - updated blueprint name
    app.register_blueprint(routes_bp)
    app.register_blueprint(projects_ui_bp)  # Now named 'projects_ui'
    
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
        logger.error(f"Server error: {str(e)}")
        if request.path.startswith('/api/'):
            return jsonify({"error": "Internal server error"}), 500
        return render_template('500.html'), 500
    
    # Add template filter for parsing JSON strings
    @app.template_filter('fromjson')
    def from_json(value):
        import json
        return json.loads(value)
    
    return app

# Create app instance
app = create_app()

# Run the application when executed directly
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)