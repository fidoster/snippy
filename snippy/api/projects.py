from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
import json
import logging
import asyncio
import time
import uuid
from lib.blob_storage import (
    save_project, get_project, get_all_projects, delete_project,
    save_section, get_sections, delete_section,
    save_article, get_articles, delete_article,
    get_search_history, get_search_results, 
    put_blob, get_blob  # Added these imports to fix undefined errors
)

# Configure logger
logger = logging.getLogger(__name__)

# Create Blueprint for REST API
projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')

# Create Blueprint for Web UI
projects_ui_bp = Blueprint('projects', __name__, url_prefix='/projects')

# API Routes
@projects_bp.route('', methods=['GET'])
def list_projects_api():
    """Get all projects"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        projects = loop.run_until_complete(get_all_projects())
        
        return jsonify({
            "status": "success",
            "projects": projects
        })
        
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('', methods=['POST'])
def create_project_api():
    """Create a new project"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        title = data.get('title')
        description = data.get('description', '')
        
        if not title:
            return jsonify({"error": "Title is required"}), 400
            
        # Create project data
        project_data = {
            "title": title,
            "description": description,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Save project
        project_id = loop.run_until_complete(save_project(project_data))
        
        if not project_id:
            return jsonify({"error": "Failed to save project"}), 500
            
        return jsonify({
            "status": "success",
            "project_id": project_id
        })
        
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('/<project_id>', methods=['GET'])
def get_project_api(project_id):
    """Get a project by ID"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        project = loop.run_until_complete(get_project(project_id))
        
        if not project:
            return jsonify({"error": "Project not found"}), 404
            
        # Get project sections
        sections = loop.run_until_complete(get_sections(project_id))
        
        return jsonify({
            "status": "success",
            "project": project,
            "sections": sections
        })
        
    except Exception as e:
        logger.error(f"Error getting project: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('/<project_id>', methods=['DELETE'])
def delete_project_api(project_id):
    """Delete a project"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        success = loop.run_until_complete(delete_project(project_id))
        
        if not success:
            return jsonify({"error": "Failed to delete project"}), 500
            
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('/<project_id>/sections', methods=['POST'])
def add_section_api(project_id):
    """Add a section to a project"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        title = data.get('title')
        
        if not title:
            return jsonify({"error": "Title is required"}), 400
            
        # Create section data
        section_data = {
            "title": title,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "articles": []
        }
        
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Save section
        section_id = loop.run_until_complete(save_section(project_id, section_data))
        
        if not section_id:
            return jsonify({"error": "Failed to save section"}), 500
            
        return jsonify({
            "status": "success",
            "section_id": section_id
        })
        
    except Exception as e:
        logger.error(f"Error adding section: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('/<project_id>/sections/<section_id>', methods=['DELETE'])
def delete_section_api(project_id, section_id):
    """Delete a section"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        success = loop.run_until_complete(delete_section(project_id, section_id))
        
        if not success:
            return jsonify({"error": "Failed to delete section"}), 500
            
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error deleting section: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('/<project_id>/sections/<section_id>/search_block', methods=['POST'])
def add_search_block_api(project_id, section_id):
    """Add a search block to a section"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        keywords = data.get('keywords')
        
        if not keywords:
            return jsonify({"error": "Keywords are required"}), 400
            
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get search results
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
        
        # Get section data
        section = loop.run_until_complete(get_blob(f"sections/{project_id}/{section_id}"))
        
        if not section:
            return jsonify({"error": "Section not found"}), 404
            
        # Add search block to section
        block_id = str(uuid.uuid4())
        search_block = {
            "id": block_id,
            "block_type": "search",
            "keywords": keywords,
            "added_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": json.dumps(results)
        }
        
        if "articles" not in section:
            section["articles"] = []
            
        section["articles"].append(search_block)
        
        # Save updated section
        success = loop.run_until_complete(put_blob(f"sections/{project_id}/{section_id}", section))
        
        if not success:
            return jsonify({"error": "Failed to save search block"}), 500
            
        return jsonify({
            "status": "success",
            "block_id": block_id
        })
        
    except Exception as e:
        logger.error(f"Error adding search block: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('/<project_id>/sections/<section_id>/search_block/<block_id>', methods=['DELETE'])
def delete_search_block_api(project_id, section_id, block_id):
    """Delete a search block from a section"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get section data
        section = loop.run_until_complete(get_blob(f"sections/{project_id}/{section_id}"))
        
        if not section:
            return jsonify({"error": "Section not found"}), 404
            
        # Remove search block
        if "articles" in section:
            section["articles"] = [a for a in section["articles"] if a.get("id") != block_id]
            
        # Save updated section
        success = loop.run_until_complete(put_blob(f"sections/{project_id}/{section_id}", section))
        
        if not success:
            return jsonify({"error": "Failed to delete search block"}), 500
            
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error deleting search block: {str(e)}")
        return jsonify({"error": str(e)}), 500

@projects_bp.route('/<project_id>/sections/<section_id>/search_block/<block_id>/article/<article_index>', methods=['DELETE'])
def delete_article_from_block_api(project_id, section_id, block_id, article_index):
    """Delete an article from a search block"""
    try:
        article_index = int(article_index)
        
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get section data
        section = loop.run_until_complete(get_blob(f"sections/{project_id}/{section_id}"))
        
        if not section:
            return jsonify({"error": "Section not found"}), 404
            
        # Find search block
        block = None
        block_index = -1
        if "articles" in section:
            for i, a in enumerate(section["articles"]):
                if a.get("id") == block_id and a.get("block_type") == "search":
                    block = a
                    block_index = i
                    break
                
        if not block:
            return jsonify({"error": "Search block not found"}), 404
            
        # Remove article from results
        results = json.loads(block["results"])
        
        if article_index < 0 or article_index >= len(results):
            return jsonify({"error": "Article index out of range"}), 400
            
        results.pop(article_index)
        
        # Update block
        section["articles"][block_index]["results"] = json.dumps(results)
        
        # Save updated section
        success = loop.run_until_complete(put_blob(f"sections/{project_id}/{section_id}", section))
        
        if not success:
            return jsonify({"error": "Failed to delete article from block"}), 500
            
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error deleting article from block: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Web UI Routes
@projects_ui_bp.route('', methods=['GET'])
def list_projects():
    """Render the projects list page"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        projects = loop.run_until_complete(get_all_projects())
        
        return render_template('projects.html', projects=projects)
        
    except Exception as e:
        logger.error(f"Error rendering projects page: {str(e)}")
        return render_template('projects.html', projects=[])

@projects_ui_bp.route('/new', methods=['GET', 'POST'])
def new_project():
    """Render the new project form or create a new project"""
    if request.method == 'GET':
        return render_template('project_form.html')
        
    # POST method
    try:
        title = request.form.get('title')
        description = request.form.get('description', '')
        
        if not title:
            flash('Title is required', 'error')
            return render_template('project_form.html')
            
        # Create project data
        project_data = {
            "title": title,
            "description": description,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Save project
        project_id = loop.run_until_complete(save_project(project_data))
        
        if not project_id:
            flash('Failed to save project', 'error')
            return render_template('project_form.html')
            
        return redirect(url_for('projects.list_projects'))
        
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return render_template('project_form.html')

@projects_ui_bp.route('/<project_id>', methods=['GET'])
def project_detail(project_id):
    """Render the project detail page"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get project data
        project = loop.run_until_complete(get_project(project_id))
        
        if not project:
            flash('Project not found', 'error')
            return redirect(url_for('projects.list_projects'))
            
        # Get project sections
        sections = loop.run_until_complete(get_sections(project_id))
        
        # Get available searches for adding to sections
        available_searches = [item.get('keywords') for item in loop.run_until_complete(get_search_history())]
        
        return render_template('project_detail.html', 
                               project=project, 
                               sections=sections, 
                               available_searches=available_searches)
        
    except Exception as e:
        logger.error(f"Error rendering project detail: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('projects.list_projects'))

@projects_ui_bp.route('/<project_id>/delete', methods=['POST'])
def delete_project_route(project_id):
    """Delete a project"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        success = loop.run_until_complete(delete_project(project_id))
        
        if not success:
            flash('Failed to delete project', 'error')
            
        return redirect(url_for('projects.list_projects'))
        
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('projects.list_projects'))

@projects_ui_bp.route('/<project_id>/section', methods=['POST'])
def add_section(project_id):
    """Add a section to a project"""
    try:
        title = request.form.get('title')
        
        if not title:
            flash('Section title is required', 'error')
            return redirect(url_for('projects.project_detail', project_id=project_id))
            
        # Create section data
        section_data = {
            "title": title,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "articles": []
        }
        
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Save section
        section_id = loop.run_until_complete(save_section(project_id, section_data))
        
        if not section_id:
            flash('Failed to save section', 'error')
            
        return redirect(url_for('projects.project_detail', project_id=project_id))
        
    except Exception as e:
        logger.error(f"Error adding section: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))

@projects_ui_bp.route('/section/<section_id>/delete', methods=['POST'])
def delete_section(section_id):
    """Delete a section"""
    try:
        # Get project_id from form or request
        project_id = request.form.get('project_id')
        
        if not project_id:
            flash('Project ID is required', 'error')
            return redirect(url_for('projects.list_projects'))
            
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        success = loop.run_until_complete(delete_section(project_id, section_id))
        
        if not success:
            flash('Failed to delete section', 'error')
            
        return redirect(url_for('projects.project_detail', project_id=project_id))
        
    except Exception as e:
        logger.error(f"Error deleting section: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('projects.list_projects'))

@projects_ui_bp.route('/<project_id>/section/<section_id>/search', methods=['POST'])
def add_search_block(project_id, section_id):
    """Add a search block to a section"""
    try:
        keywords = request.form.get('keywords')
        
        if not keywords:
            flash('Keywords are required', 'error')
            return redirect(url_for('projects.project_detail', project_id=project_id))
            
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get search results
        history_data = loop.run_until_complete(get_search_history())
        
        search_id = None
        for item in history_data:
            if item.get('keywords') == keywords:
                search_id = item.get('id')
                break
        
        if not search_id:
            flash('Search not found', 'error')
            return redirect(url_for('projects.project_detail', project_id=project_id))
        
        # Get search results
        results = loop.run_until_complete(get_search_results(search_id))
        
        # Get section data
        section = loop.run_until_complete(get_blob(f"sections/{project_id}/{section_id}"))
        
        if not section:
            flash('Section not found', 'error')
            return redirect(url_for('projects.project_detail', project_id=project_id))
            
        # Add search block to section
        block_id = str(uuid.uuid4())
        search_block = {
            "id": block_id,
            "block_type": "search",
            "keywords": keywords,
            "added_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": json.dumps(results)
        }
        
        if "articles" not in section:
            section["articles"] = []
            
        section["articles"].append(search_block)
        
        # Save updated section
        success = loop.run_until_complete(put_blob(f"sections/{project_id}/{section_id}", section))
        
        if not success:
            flash('Failed to save search block', 'error')
            
        return redirect(url_for('projects.project_detail', project_id=project_id))
        
    except Exception as e:
        logger.error(f"Error adding search block: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))

@projects_ui_bp.route('/<project_id>/section/<section_id>/article/<article_id>/delete', methods=['POST'])
def delete_article_route(project_id, section_id, article_id):
    """Delete an article (search block) from a section"""
    try:
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get section data
        section = loop.run_until_complete(get_blob(f"sections/{project_id}/{section_id}"))
        
        if not section:
            flash('Section not found', 'error')
            return redirect(url_for('projects.project_detail', project_id=project_id))
            
        # Remove article
        if "articles" in section:
            section["articles"] = [a for a in section["articles"] if a.get("id") != article_id]
            
        # Save updated section
        success = loop.run_until_complete(put_blob(f"sections/{project_id}/{section_id}", section))
        
        if not success:
            flash('Failed to delete article', 'error')
            
        return redirect(url_for('projects.project_detail', project_id=project_id))
        
    except Exception as e:
        logger.error(f"Error deleting article: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))

@projects_ui_bp.route('/<project_id>/section/<section_id>/block/<block_id>/article/<article_index>/delete', methods=['POST'])
def delete_article_from_block(project_id, section_id, block_id, article_index):
    """Delete an article from a search block"""
    try:
        article_index = int(article_index)
        
        # Use asyncio to run async functions
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get section data
        section = loop.run_until_complete(get_blob(f"sections/{project_id}/{section_id}"))
        
        if not section:
            flash('Section not found', 'error')
            return redirect(url_for('projects.project_detail', project_id=project_id))
            
        # Find search block
        block = None
        block_index = -1
        if "articles" in section:
            for i, a in enumerate(section["articles"]):
                if a.get("id") == block_id and a.get("block_type") == "search":
                    block = a
                    block_index = i
                    break
                
        if not block:
            flash('Search block not found', 'error')
            return redirect(url_for('projects.project_detail', project_id=project_id))
            
        # Remove article from results
        results = json.loads(block["results"])
        
        if article_index < 0 or article_index >= len(results):
            flash('Article index out of range', 'error')
            return redirect(url_for('projects.project_detail', project_id=project_id))
            
        results.pop(article_index)
        
        # Update block
        section["articles"][block_index]["results"] = json.dumps(results)
        
        # Save updated section
        success = loop.run_until_complete(put_blob(f"sections/{project_id}/{section_id}", section))
        
        if not success:
            flash('Failed to delete article from block', 'error')
            
        return redirect(url_for('projects.project_detail', project_id=project_id))
        
    except Exception as e:
        logger.error(f"Error deleting article from block: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))