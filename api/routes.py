# api/routes.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for
import logging
import asyncio
from lib.blob_storage import get_search_history

# Configure logger
logger = logging.getLogger(__name__)

# Create Blueprint
routes_bp = Blueprint('routes', __name__)

@routes_bp.route('/', methods=['GET'])
def index():
    """Render the main search page"""
    return jsonify({"status": "ok", "message": "Snippy API index route"})

@routes_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok", 
        "message": "Snippy API is healthy",
        "version": "1.0.0"
    })