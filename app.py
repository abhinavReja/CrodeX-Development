import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import uuid
import zipfile
import io
from datetime import datetime

# Get the directory where this app.py file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Explicitly set template and static folders
app = Flask(__name__, 
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)

# Set secret key for sessions
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# In-memory storage for demo (use database in production)
tasks = {}
files = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET':
        return render_template('upload.html')
    
    # Handle file upload
    if 'file' not in request.files:
        if request.is_json or 'application/json' in request.headers.get('Content-Type', ''):
            return jsonify({'error': 'No file provided'}), 400
        flash('No file provided', 'error')
        return redirect(url_for('upload'))
    
    file = request.files['file']
    if file.filename == '':
        if request.is_json or 'application/json' in request.headers.get('Content-Type', ''):
            return jsonify({'error': 'No file selected'}), 400
        flash('No file selected', 'error')
        return redirect(url_for('upload'))
    
    # Validate file type (ZIP only)
    if not file.filename.endswith('.zip'):
        if request.is_json or 'application/json' in request.headers.get('Content-Type', ''):
            return jsonify({'error': 'Only ZIP files are allowed'}), 400
        flash('Only ZIP files are allowed', 'error')
        return redirect(url_for('upload'))
    
    # Read file content to get size
    file_content = file.read()
    file_size = len(file_content)
    
    # Validate file size (100MB max)
    max_size = 100 * 1024 * 1024
    if file_size > max_size:
        if request.is_json or 'application/json' in request.headers.get('Content-Type', ''):
            return jsonify({'error': f'File size exceeds {max_size / (1024*1024)}MB limit'}), 400
        flash(f'File size exceeds {max_size / (1024*1024)}MB limit', 'error')
        return redirect(url_for('upload'))
    
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
        'redirect_url': url_for('context_form', file_id=file_id),
        'structure': files[file_id].get('structure', [])
    }), 200

@app.route('/context/<file_id>', methods=['GET', 'POST'])
def context_form(file_id):
    if request.method == 'GET':
        if file_id not in files:
            flash('File not found', 'error')
            return redirect(url_for('upload'))
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
            'redirect_url': url_for('progress', task_id=task_id)
        }), 200
    
    return redirect(url_for('progress', task_id=task_id))

@app.route('/progress/<task_id>')
def progress(task_id):
    if task_id not in tasks:
        flash('Task not found', 'error')
        return redirect(url_for('index'))
    return render_template('progress.html', task_id=task_id)

@app.route('/download/<file_id>')
def download_file(file_id):
    if file_id not in files:
        flash('File not found', 'error')
        return redirect(url_for('index'))
    
    file_info = files[file_id]
    return render_template('download.html', 
                         file_id=file_id,
                         original_name=file_info['name'],
                         processed_name=file_info['name'],
                         file_size=file_info['size'])

# API Routes
@app.route('/api/progress/<task_id>')
def api_progress(task_id):
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    return jsonify({
        'progress': task.get('progress', 0),
        'status': task.get('status', 'pending'),
        'status_message': task.get('status_message', 'Processing...'),
        'step': task.get('step', 1),
        'files': task.get('files', []),
        'file_id': task.get('file_id')
    }), 200

@app.route('/api/progress/stream/<task_id>')
def api_progress_stream(task_id):
    """Server-Sent Events stream for real-time progress updates"""
    from flask import Response
    import json
    import time
    
    def generate():
        while True:
            if task_id not in tasks:
                yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
                break
            
            task = tasks[task_id]
            data = {
                'progress': task.get('progress', 0),
                'status': task.get('status', 'pending'),
                'status_message': task.get('status_message', 'Processing...'),
                'step': task.get('step', 1),
                'files': task.get('files', []),
            }
            
            yield f"data: {json.dumps(data)}\n\n"
            
            if task.get('status') in ['completed', 'failed', 'cancelled']:
                break
            
            time.sleep(1)  # Update every second
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/file-analysis/<file_id>')
def api_file_analysis(file_id):
    """Return auto-suggestions based on file analysis"""
    if file_id not in files:
        return jsonify({'error': 'File not found'}), 404
    
    # Mock suggestions (replace with actual analysis)
    suggestions = {
        'context_type': 'archive',
        'description': 'ZIP archive file',
        'features': ['extract', 'compress']
    }
    
    return jsonify({'suggestions': suggestions}), 200

@app.route('/api/autocomplete/description')
def api_autocomplete_description():
    """Return autocomplete suggestions for description field"""
    query = request.args.get('q', '').lower()
    
    # Mock suggestions (replace with actual autocomplete logic)
    suggestions = [
        'ZIP archive containing multiple files',
        'Archive file for processing',
        'Compressed file archive'
    ]
    
    filtered = [s for s in suggestions if query in s.lower()][:5]
    return jsonify({'suggestions': filtered}), 200

@app.route('/api/cancel/<task_id>', methods=['POST'])
def api_cancel_task(task_id):
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    tasks[task_id]['status'] = 'cancelled'
    return jsonify({'message': 'Task cancelled'}), 200

@app.route('/api/zip-structure/<file_id>')
def api_zip_structure(file_id):
    """Return the structure of a ZIP file"""
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

def parse_zip_structure(zip_content):
    """Parse ZIP file and return its structure as a tree with dashes"""
    structure = []
    
    try:
        zip_file = zipfile.ZipFile(io.BytesIO(zip_content))
        file_list = sorted(zip_file.namelist())
        
        # Build a tree structure
        tree = {}
        file_sizes = {}
        
        # Collect file sizes
        for file_path in file_list:
            if not file_path.endswith('/'):
                try:
                    info = zip_file.getinfo(file_path)
                    file_sizes[file_path] = info.file_size
                except:
                    file_sizes[file_path] = 0
        
        # Build directory tree
        for file_path in file_list:
            if file_path.endswith('/'):
                continue
            
            parts = file_path.split('/')
            current = tree
            
            # Navigate/create directory structure
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {'type': 'dir', 'children': {}}
                elif current[part].get('type') != 'dir':
                    # Convert to directory if it was a file
                    current[part] = {'type': 'dir', 'children': {}}
                elif 'children' not in current[part]:
                    current[part]['children'] = {}
                current = current[part]['children']
            
            # Add file (handle root level files)
            filename = parts[-1]
            if len(parts) == 1:
                # Root level file
                if filename not in tree:
                    tree[filename] = {
                        'type': 'file',
                        'size': file_sizes.get(file_path, 0),
                        'path': file_path
                    }
            else:
                # File in a directory
                if filename not in current:
                    current[filename] = {
                        'type': 'file',
                        'size': file_sizes.get(file_path, 0),
                        'path': file_path
                    }
        
        # Convert tree to flat list with dashes
        def traverse_tree(node, depth=0, parent_path=''):
            result = []
            items = sorted(node.items(), key=lambda x: (x[1].get('type') == 'file', x[0].lower()))
            
            for name, item in items:
                dashes = '--' * depth
                prefix = f"{dashes} " if dashes else ""
                
                if item['type'] == 'dir':
                    display = f"{prefix}{name}/"
                    result.append({
                        'name': name,
                        'path': f"{parent_path}/{name}" if parent_path else name,
                        'display': display,
                        'depth': depth,
                        'is_file': False,
                        'size': 0
                    })
                    
                    # Add children
                    if 'children' in item:
                        result.extend(traverse_tree(item['children'], depth + 1, 
                                                   f"{parent_path}/{name}" if parent_path else name))
                else:
                    # It's a file
                    size_str = f" ({format_size(item['size'])})" if item['size'] > 0 else ""
                    display = f"{prefix}{name}{size_str}"
                    result.append({
                        'name': name,
                        'path': item.get('path', name),
                        'display': display,
                        'depth': depth,
                        'is_file': True,
                        'size': item['size']
                    })
            
            return result
        
        structure = traverse_tree(tree)
        zip_file.close()
        
    except Exception as e:
        print(f"Error parsing ZIP: {e}")
        import traceback
        traceback.print_exc()
        structure = []
    
    return structure

def format_size(size_bytes):
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
