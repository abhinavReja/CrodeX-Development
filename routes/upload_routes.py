from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import uuid
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import shared storage and utilities
from storage import files, tasks
from utils.zip_parser import parse_zip_structure

upload_bp = Blueprint('upload', __name__)
api_upload_bp = Blueprint('api_upload', __name__)

@upload_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """Handle file upload - Template route"""
    if request.method == 'GET':
        return render_template('upload.html')
    
    # Handle file upload
    if 'file' not in request.files:
        if request.is_json or 'application/json' in request.headers.get('Content-Type', ''):
            return jsonify({'error': 'No file provided'}), 400
        flash('No file provided', 'error')
        return redirect(url_for('upload.upload'))
    
    file = request.files['file']
    if file.filename == '':
        if request.is_json or 'application/json' in request.headers.get('Content-Type', ''):
            return jsonify({'error': 'No file selected'}), 400
        flash('No file selected', 'error')
        return redirect(url_for('upload.upload'))
    
    # Validate file type (ZIP only)
    if not file.filename.endswith('.zip'):
        if request.is_json or 'application/json' in request.headers.get('Content-Type', ''):
            return jsonify({'error': 'Only ZIP files are allowed'}), 400
        flash('Only ZIP files are allowed', 'error')
        return redirect(url_for('upload.upload'))
    
    # Read file content to get size
    file_content = file.read()
    file_size = len(file_content)
    
    # Validate file size (100MB max)
    max_size = 100 * 1024 * 1024
    if file_size > max_size:
        if request.is_json or 'application/json' in request.headers.get('Content-Type', ''):
            return jsonify({'error': f'File size exceeds {max_size / (1024*1024)}MB limit'}), 400
        flash(f'File size exceeds {max_size / (1024*1024)}MB limit', 'error')
        return redirect(url_for('upload.upload'))
    
    # Generate file ID
    file_id = str(uuid.uuid4())
    
    # Store file info (in production, save to disk/database)
    files[file_id] = {
        'id': file_id,
        'name': file.filename,
        'size': file_size,
        'uploaded_at': datetime.now().isoformat(),
        'content': file_content  # In production, save to disk
    }
    
    # Parse ZIP file structure
    try:
        zip_structure = parse_zip_structure(file_content)
        files[file_id]['structure'] = zip_structure
    except Exception as e:
        print(f"Error parsing ZIP structure: {e}")
        files[file_id]['structure'] = []
    
    # Return JSON response for AJAX (upload.js expects this)
    return jsonify({
        'file_id': file_id,
        'redirect_url': url_for('analysis.analysis_results', file_id=file_id),
        'structure': files[file_id].get('structure', [])
    }), 200

# API routes (registered with /api prefix)
@api_upload_bp.route('/upload', methods=['POST'])
def api_upload():
    """Handle file upload - API route"""
    # Handle file upload
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file type (ZIP only)
    if not file.filename.endswith('.zip'):
        return jsonify({'error': 'Only ZIP files are allowed'}), 400
    
    # Read file content to get size
    file_content = file.read()
    file_size = len(file_content)
    
    # Validate file size (100MB max)
    max_size = 100 * 1024 * 1024
    if file_size > max_size:
        return jsonify({'error': f'File size exceeds {max_size / (1024*1024)}MB limit'}), 400
    
    # Generate file ID
    file_id = str(uuid.uuid4())
    
    # Store file info (in production, save to disk/database)
    files[file_id] = {
        'id': file_id,
        'name': file.filename,
        'size': file_size,
        'uploaded_at': datetime.now().isoformat(),
        'content': file_content  # In production, save to disk
    }
    
    # Parse ZIP file structure
    try:
        zip_structure = parse_zip_structure(file_content)
        files[file_id]['structure'] = zip_structure
    except Exception as e:
        print(f"Error parsing ZIP structure: {e}")
        files[file_id]['structure'] = []
    
    # Return JSON response
    return jsonify({
        'file_id': file_id,
        'redirect_url': url_for('analysis.analysis_results', file_id=file_id),
        'structure': files[file_id].get('structure', [])
    }), 200

@api_upload_bp.route('/zip-structure/<file_id>')
def zip_structure(file_id):
    """Return the structure of a ZIP file - API route"""
    if file_id not in files:
        return jsonify({'error': 'File not found'}), 404
    
    file_info = files[file_id]
    
    # If structure is already parsed, return it
    if 'structure' in file_info:
        return jsonify({'structure': file_info['structure']}), 200
    
    # Otherwise, parse it now
    try:
        if 'content' in file_info:
            structure = parse_zip_structure(file_info['content'])
            files[file_id]['structure'] = structure
            return jsonify({'structure': structure}), 200
        else:
            return jsonify({'error': 'File content not available'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
