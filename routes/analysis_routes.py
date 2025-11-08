from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
import uuid
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import shared storage
from storage import files, tasks

analysis_bp = Blueprint('analysis', __name__)
api_analysis_bp = Blueprint('api_analysis', __name__)

@analysis_bp.route('/context/<file_id>', methods=['GET', 'POST'])
def context_form(file_id):
    """Handle context form - Template route"""
    if request.method == 'GET':
        if file_id not in files:
            flash('File not found', 'error')
            return redirect(url_for('upload.upload'))
        return render_template('context_form.html', file_id=file_id)
    
    # Handle form submission
    data = request.get_json() if request.is_json else request.form.to_dict()
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        'id': task_id,
        'file_id': file_id,
        'context': data,
        'status': 'processing',
        'progress': 0,
        'step': 1,
        'created_at': datetime.now().isoformat(),
        'files': []
    }
    
    if request.is_json:
        return jsonify({
            'task_id': task_id,
            'redirect_url': url_for('conversion.progress', task_id=task_id)
        }), 200
    
    return redirect(url_for('conversion.progress', task_id=task_id))

# API routes (registered with /api prefix)
@api_analysis_bp.route('/file-analysis/<file_id>', methods=['GET'])
@api_analysis_bp.route('/analyze/<file_id>', methods=['GET'])
def analyze_file(file_id):
    """Return auto-suggestions based on file analysis - API route"""
    if file_id not in files:
        return jsonify({'error': 'File not found'}), 404
    
    # Mock suggestions (replace with actual analysis)
    suggestions = {
        'context_type': 'archive',
        'description': 'ZIP archive file',
        'features': ['extract', 'compress']
    }
    
    return jsonify({'suggestions': suggestions}), 200

@api_analysis_bp.route('/autocomplete/description', methods=['GET'])
def autocomplete_description():
    """Return autocomplete suggestions for description field - API route"""
    query = request.args.get('q', '').lower()
    
    # Mock suggestions (replace with actual autocomplete logic)
    suggestions = [
        'ZIP archive containing multiple files',
        'Archive file for processing',
        'Compressed file archive'
    ]
    
    filtered = [s for s in suggestions if query in s.lower()][:5]
    return jsonify({'suggestions': filtered}), 200

@api_analysis_bp.route('/confirm-context', methods=['POST'])
def confirm_context():
    """Confirm context and start conversion"""
    data = request.get_json()
    file_id = data.get('file_id')
    
    if not file_id or file_id not in files:
        return jsonify({'error': 'File not found'}), 404
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        'id': task_id,
        'file_id': file_id,
        'context': data,
        'status': 'pending',
        'progress': 0,
        'step': 1,
        'created_at': datetime.now().isoformat(),
        'files': []
    }
    
    return jsonify({
        'task_id': task_id,
        'status': 'pending'
    }), 200

