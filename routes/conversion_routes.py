from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, Response
import json
import time
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import shared storage
from storage import tasks

conversion_bp = Blueprint('conversion', __name__)
api_conversion_bp = Blueprint('api_conversion', __name__)

# Template route for progress page (no prefix)
@conversion_bp.route('/progress/<task_id>', methods=['GET'])
def progress(task_id):
    """Display progress page - Template route"""
    if task_id not in tasks:
        flash('Task not found', 'error')
        return redirect(url_for('main.index'))
    return render_template('progress.html', task_id=task_id)

# API routes (will be registered with /api prefix)
@api_conversion_bp.route('/progress/<task_id>', methods=['GET'])
def progress_status_api(task_id):
    """Get conversion status - API route"""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    files = task.get('files', [])
    
    # Calculate files processed count
    files_processed = len([f for f in files if f.get('status') == 'completed'])
    
    # Calculate warnings count
    warnings = task.get('warnings', 0)
    
    return jsonify({
        'task_id': task_id,
        'progress': task.get('progress', 0),
        'status': task.get('status', 'pending'),
        'status_message': task.get('status_message', 'Processing...'),
        'step': task.get('step', 1),
        'files': files,
        'file_id': task.get('file_id'),
        'warnings': warnings,
        'files_processed': files_processed,
        'log_message': task.get('log_message'),
        'log_level': task.get('log_level', 'info')
    }), 200

@api_conversion_bp.route('/progress/stream/<task_id>')
def progress_stream(task_id):
    """Server-Sent Events stream for real-time progress updates"""
    
    def generate():
        while True:
            if task_id not in tasks:
                yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
                break
            
            task = tasks[task_id]
            files = task.get('files', [])
            files_processed = len([f for f in files if f.get('status') == 'completed'])
            warnings = task.get('warnings', 0)
            
            data = {
                'progress': task.get('progress', 0),
                'status': task.get('status', 'pending'),
                'status_message': task.get('status_message', 'Processing...'),
                'step': task.get('step', 1),
                'files': files,
                'file_id': task.get('file_id'),
                'warnings': warnings,
                'files_processed': files_processed,
                'log_message': task.get('log_message'),
                'log_level': task.get('log_level', 'info')
            }
            
            yield f"data: {json.dumps(data)}\n\n"
            
            if task.get('status') in ['completed', 'failed', 'cancelled']:
                break
            
            time.sleep(1)  # Update every second
    
    return Response(generate(), mimetype='text/event-stream')

@api_conversion_bp.route('/convert', methods=['POST'])
def convert():
    """Start conversion process"""
    data = request.get_json()
    task_id = data.get('task_id')
    
    if not task_id or task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    # Update task status
    tasks[task_id]['status'] = 'processing'
    tasks[task_id]['step'] = 2
    
    return jsonify({
        'task_id': task_id,
        'status': 'processing'
    }), 200

@api_conversion_bp.route('/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    """Cancel a conversion task - API route"""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    tasks[task_id]['status'] = 'cancelled'
    return jsonify({'message': 'Task cancelled'}), 200

