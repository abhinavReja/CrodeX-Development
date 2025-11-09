from flask import Blueprint, request, jsonify, session, current_app, render_template
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

from schemas.upload_schema import UploadValidator
from middleware.validation import validate_request

# If you actually use Gemini or FileManager, keep the import. If not, remove it.
# from services.gemini_api import GeminiService
from utils.file_manager import FileManager   # ← keep this if you use it

upload_bp = Blueprint('upload', __name__)

# ── GET /upload: render the page (lets your "Get Started" button work)
@upload_bp.route('/upload', methods=['GET'])
def upload_page():
    return render_template('upload.html')

# ── POST /upload: handle the upload
# NOTE: endpoint='upload' so url_for('upload.upload') works (your templates expect this)
@upload_bp.route('/upload', methods=['POST'], endpoint='upload')
@validate_request(UploadValidator)
def upload_project():
    """
    Upload and extract project archive

    Request:
        - file: archive file (multipart/form-data)

    Response:
        {
            "status": "success",
            "project_id": "uuid",
            "message": "Project uploaded successfully",
            "file_info": {
                "filename": "project.zip",
                "size": 1024000,
                "files_count": 45
            }
        }
    """
    try:
        # Get uploaded file
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400

        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400

        # Validate extension against config
        if not allowed_file(file.filename):
            allowed = ', '.join(sorted(current_app.config['ALLOWED_EXTENSIONS']))
            return jsonify({
                'status': 'error',
                'message': f'Invalid file type. Allowed: {allowed}.'
            }), 400

        # Generate unique project ID
        project_id = str(uuid.uuid4())

        # Initialize file manager
        file_manager = FileManager(current_app.config['UPLOAD_FOLDER'])

        # Create project directory
        project_path = file_manager.create_project_directory(project_id)
        project_path_str = str(project_path)  # Convert to string for use with os.path

        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(project_path_str, filename)
        file.save(file_path)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Extract archive (assumes FileManager handles .zip; extend if you added more types)
        extracted_path = file_manager.extract_zip(file_path, project_path_str)
        extracted_path_str = str(extracted_path)  # Convert to string for subsequent operations

        # Count extracted files
        files_count = file_manager.count_files(extracted_path_str)

        # Load file contents
        files_dict = file_manager.load_files(extracted_path_str)

        # CRITICAL: Clear any previous conversion results when uploading new project
        # This ensures we don't accidentally use old converted files
        if 'converted_path' in session:
            del session['converted_path']
        if 'conversion_result' in session:
            del session['conversion_result']
        if 'conversion_complete' in session:
            del session['conversion_complete']
        
        # Store in session (convert Path objects to strings for JSON serialization)
        session['project_id'] = project_id
        session['project_path'] = project_path_str  # Already converted to string
        session['extracted_path'] = extracted_path_str  # Already converted to string
        session['upload_timestamp'] = datetime.now().isoformat()
        session['files_dict'] = files_dict
        session['original_filename'] = filename  # Store original filename for download
        session.modified = True
        
        # Log what was stored
        current_app.logger.info(f"Stored {len(files_dict)} files in session for project {project_id}")
        if files_dict:
            sample_keys = list(files_dict.keys())[:5]
            current_app.logger.info(f"Sample files stored: {sample_keys}")

        # Perform quick local analysis immediately after upload (no AI call to save time/API)
        try:
            from services.analyzer import FrameworkAnalyzer
            analyzer = FrameworkAnalyzer()
            local_analysis = analyzer.analyze_structure(files_dict)
            
            # Store basic analysis in session
            session['analysis'] = {
                'framework': local_analysis.get('primary_framework', 'Unknown'),
                'confidence': local_analysis.get('confidence', 0),
                'structure': local_analysis.get('structure', {}),
                'dependencies': local_analysis.get('dependencies', []),
                'database': local_analysis.get('database', {}),
                'file_stats': local_analysis.get('file_stats', {}),
                'notes': local_analysis.get('notes', '')
            }
            session.modified = True
            current_app.logger.info(f"Quick analysis completed for {project_id}: {session['analysis'].get('framework')}")
        except Exception as e:
            current_app.logger.warning(f"Quick analysis failed for {project_id}: {str(e)}")
            # Continue without analysis - it can be done later

        current_app.logger.info(f"Project uploaded: {project_id} - {files_count} files")

        # Generate redirect URL for context form
        from flask import url_for
        redirect_url = url_for('analysis.context_form', project_id=project_id)

        return jsonify({
            'status': 'success',
            'project_id': project_id,
            'message': 'Project uploaded successfully',
            'redirect_url': redirect_url,
            'file_info': {
                'filename': filename,
                'size': file_size,
                'files_count': files_count
            }
        }), 201

    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Upload failed: {str(e)}'}), 500


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed based on config."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config['ALLOWED_EXTENSIONS']


# API route for ZIP structure - needs to be accessible from upload_bp
# This will be registered with /api prefix when upload_bp is registered
# But we need to make it accessible without prefix, so we'll register it separately in app.py
def get_zip_structure(project_id):
    """
    Get ZIP file structure for a project
    
    Response:
        {
            "status": "success",
            "structure": [
                {
                    "name": "file.py",
                    "path": "file.py",
                    "display": "file.py (1.2 KB)",
                    "depth": 0,
                    "is_file": true,
                    "size": 1234
                },
                ...
            ]
        }
    """
    try:
        # Verify project belongs to session
        session_project_id = session.get('project_id')
        
        if session_project_id != project_id:
            return jsonify({
                'status': 'error',
                'message': 'Invalid project ID'
            }), 403
        
        # Get extracted path from session
        extracted_path = session.get('extracted_path')
        
        if not extracted_path:
            return jsonify({
                'status': 'error',
                'message': 'Project not found or not extracted'
            }), 404
        
        # Get directory structure using FileManager
        file_manager = FileManager(current_app.config['UPLOAD_FOLDER'])
        
        # Get structure as nested dictionary
        structure_tree = file_manager.get_directory_structure(extracted_path, max_depth=5)
        
        # Convert nested structure to flat list with display format
        structure_list = []
        
        def flatten_structure(node, parent_path='', depth=0):
            """Convert nested structure to flat list"""
            if not isinstance(node, dict) or not node:
                return
            
            # Handle root level - it might be a directory or have children
            if 'type' in node:
                # Single file or directory node
                if node.get('type') == 'file':
                    size = node.get('size', 0)
                    size_str = f" ({_format_size(size)})" if size > 0 else ""
                    display = parent_path.split('/')[-1] if parent_path else "file"
                    structure_list.append({
                        'name': display,
                        'path': parent_path,
                        'display': display + size_str,
                        'depth': depth,
                        'is_file': True,
                        'size': size
                    })
                elif node.get('type') == 'directory' and 'children' in node:
                    # Directory with children
                    if parent_path:
                        name = parent_path.split('/')[-1]
                        dashes = '--' * depth
                        prefix = f"{dashes} " if dashes else ""
                        display = f"{prefix}{name}/"
                        structure_list.append({
                            'name': name,
                            'path': parent_path,
                            'display': display,
                            'depth': depth,
                            'is_file': False,
                            'size': 0
                        })
                    # Process children
                    for child_name, child_node in sorted(node['children'].items(), 
                                                          key=lambda x: (x[1].get('type') != 'directory', x[0].lower())):
                        child_path = f"{parent_path}/{child_name}" if parent_path else child_name
                        flatten_structure(child_node, child_path, depth + 1)
            else:
                # Root level - process all items
                items = sorted(node.items(), key=lambda x: (
                    x[1].get('type') != 'directory' if isinstance(x[1], dict) and 'type' in x[1] else True,
                    x[0].lower()
                ))
                
                for name, item in items:
                    current_path = f"{parent_path}/{name}" if parent_path else name
                    dashes = '--' * depth
                    prefix = f"{dashes} " if dashes else ""
                    
                    if isinstance(item, dict):
                        if item.get('type') == 'directory':
                            display = f"{prefix}{name}/"
                            structure_list.append({
                                'name': name,
                                'path': current_path,
                                'display': display,
                                'depth': depth,
                                'is_file': False,
                                'size': 0
                            })
                            
                            # Recursively process children
                            if 'children' in item:
                                flatten_structure(item['children'], current_path, depth + 1)
                        elif item.get('type') == 'file':
                            # It's a file
                            size = item.get('size', 0)
                            size_str = f" ({_format_size(size)})" if size > 0 else ""
                            display = f"{prefix}{name}{size_str}"
                            structure_list.append({
                                'name': name,
                                'path': current_path,
                                'display': display,
                                'depth': depth,
                                'is_file': True,
                                'size': size
                            })
        
        flatten_structure(structure_tree)
        
        # If structure_list is empty, try a simpler approach - list files directly
        if not structure_list:
            try:
                from pathlib import Path as PathLib
                extracted_path_obj = PathLib(extracted_path)
                if extracted_path_obj.exists():
                    # List files directly
                    for file_path in extracted_path_obj.rglob('*'):
                        if file_path.is_file():
                            relative_path = file_path.relative_to(extracted_path_obj)
                            depth = len(relative_path.parts) - 1
                            dashes = '--' * depth
                            prefix = f"{dashes} " if dashes else ""
                            size = file_path.stat().st_size
                            size_str = f" ({_format_size(size)})" if size > 0 else ""
                            
                            structure_list.append({
                                'name': relative_path.name,
                                'path': str(relative_path),
                                'display': f"{prefix}{relative_path}{size_str}",
                                'depth': depth,
                                'is_file': True,
                                'size': size
                            })
            except Exception as e:
                current_app.logger.error(f"Error listing files directly: {str(e)}")
        
        return jsonify({
            'status': 'success',
            'structure': structure_list
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting ZIP structure: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error getting structure: {str(e)}'
        }), 500


def _format_size(size_bytes: int) -> str:
    """Format file size to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"