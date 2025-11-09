from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_file
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import shared storage
from storage import files, tasks

download_bp = Blueprint('download', __name__)
api_download_bp = Blueprint('api_download', __name__)

@download_bp.route('/download/<file_id>', methods=['GET'])
def download_file(file_id):
    """Download page and file download"""
    if file_id not in files:
        flash('File not found', 'error')
        return redirect(url_for('main.index'))
    
    file_info = files[file_id]
    
    # If it's a download request (with download parameter)
    if request.args.get('download') == 'true':
        # Return file for download
        if 'content' in file_info:
            from io import BytesIO
            return send_file(
                BytesIO(file_info['content']),
                mimetype='application/zip',
                as_attachment=True,
                download_name=file_info['name']
            )
        else:
            flash('File content not available', 'error')
            return redirect(url_for('download.download_file', file_id=file_id))
    
    # Find associated task for this file
    task_info = None
    for task_id, task in tasks.items():
        if task.get('file_id') == file_id:
            task_info = task
            break
    
    # Calculate files processed count from task
    files_processed = 0
    if task_info:
        task_files = task_info.get('files', [])
        files_processed = len([f for f in task_files if f.get('status') == 'completed'])
    
    # Otherwise, show download page
    return render_template('download.html', 
                         file_id=file_id,
                         original_name=file_info['name'],
                         processed_name=file_info['name'],
                         file_size=file_info['size'],
                         files_processed=files_processed,
                         task_info=task_info)

# API routes (registered with /api prefix)
@api_download_bp.route('/download/<file_id>', methods=['GET'])
def download_file_content(file_id):
    """Download the actual file - API route"""
    if file_id not in files:
        return jsonify({'error': 'File not found'}), 404
    
    file_info = files[file_id]
    
    if 'content' not in file_info:
        return jsonify({'error': 'File content not available'}), 404
    
    from io import BytesIO
    return send_file(
        BytesIO(file_info['content']),
        mimetype='application/zip',
        as_attachment=True,
        download_name=file_info['name']
    )

