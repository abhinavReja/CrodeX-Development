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

@analysis_bp.route('/analysis/<file_id>', methods=['GET'])
def analysis_results(file_id):
    """Display analysis results page - Template route"""
    if file_id not in files:
        flash('File not found', 'error')
        return redirect(url_for('upload.upload'))
    return render_template('analysis.html', file_id=file_id)

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
        'status': 'pending',
        'progress': 0,
        'step': 1,
        'created_at': datetime.now().isoformat(),
        'files': []
    }
    
    if request.is_json:
        return jsonify({
            'task_id': task_id,
            'redirect_url': url_for('conversion.progress', task_id=task_id),
            'status': 'success'
        }), 200
    
    return redirect(url_for('conversion.progress', task_id=task_id))

# API routes (registered with /api prefix)
@api_analysis_bp.route('/file-analysis/<file_id>', methods=['GET'])
@api_analysis_bp.route('/analyze/<file_id>', methods=['GET'])
def analyze_file(file_id):
    """Return full analysis results based on file analysis - API route"""
    if file_id not in files:
        return jsonify({'error': 'File not found'}), 404
    
    # Mock analysis data (replace with actual analysis)
    analysis = {
        'framework': 'Laravel 10.x',
        'confidence': 95,
        'structure': {
            'components': {
                'controllers': ['UserController.php', 'PostController.php', 'CommentController.php'],
                'models': ['User.php', 'Post.php', 'Comment.php', 'Category.php'],
                'views': ['index.blade.php', 'show.blade.php', 'create.blade.php'],
                'routes': ['web.php', 'api.php', 'console.php']
            }
        },
        'dependencies': [
            'laravel/framework@^10.0',
            'guzzlehttp/guzzle@^7.0',
            'spatie/laravel-permission@^6.0',
            'barryvdh/laravel-debugbar@^3.8'
        ],
        'database': {
            'type': 'MySQL',
            'migrations_found': True,
            'tables': ['users', 'posts', 'comments', 'categories']
        },
        'notes': 'Routes use REST naming. Translate middleware & policies to the target framework. Blade components map to Jinja2 includes.'
    }
    
    return jsonify({'analysis': analysis}), 200

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
