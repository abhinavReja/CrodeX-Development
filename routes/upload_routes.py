from flask import Blueprint, request, jsonify, session, current_app, render_template
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

from schemas.upload_schema import UploadValidator
from middleware.validation import validate_request

# If you actually use Gemini or FileManager, keep the import. If not, remove it.
# from services.gemini_api import GeminiService
# from utils.file_manager import FileManager   # ← keep this if you use it

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

        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(project_path, filename)
        file.save(file_path)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Extract archive (assumes FileManager handles .zip; extend if you added more types)
        extracted_path = file_manager.extract_zip(file_path, project_path)

        # Count extracted files
        files_count = file_manager.count_files(extracted_path)

        # Load file contents
        files_dict = file_manager.load_files(extracted_path)

        # Store in session
        session['project_id'] = project_id
        session['project_path'] = project_path
        session['extracted_path'] = extracted_path
        session['upload_timestamp'] = datetime.now().isoformat()
        session['files_dict'] = files_dict
        session.modified = True

        current_app.logger.info(f"Project uploaded: {project_id} - {files_count} files")

        return jsonify({
            'status': 'success',
            'project_id': project_id,
            'message': 'Project uploaded successfully',
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
