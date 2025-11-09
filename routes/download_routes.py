from flask import Blueprint, send_file, session, current_app, jsonify
import os
import zipfile
import io
from utils.file_manager import FileManager

download_bp = Blueprint('download', __name__)

@download_bp.route('/download/<project_id>', methods=['GET'])
def download_converted_project(project_id):
    """
    Download converted project as ZIP
    
    Response:
        ZIP file stream
    """
    
    try:
        # Verify project
        session_project_id = session.get('project_id')
        
        if session_project_id != project_id:
            return jsonify({
                'status': 'error',
                'message': 'Invalid project ID'
            }), 403
        
        # Check if conversion is complete
        if not session.get('conversion_complete'):
            return jsonify({
                'status': 'error',
                'message': 'Conversion not complete'
            }), 400
        
        # Get converted files path
        converted_path = session.get('converted_path')
        
        if not converted_path or not os.path.exists(converted_path):
            return jsonify({
                'status': 'error',
                'message': 'Converted files not found'
            }), 404
        
        # Create ZIP file in memory
        current_app.logger.info(f"Creating ZIP for download: {project_id}")
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add all converted files
            for root, dirs, files in os.walk(converted_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, converted_path)
                    zip_file.write(file_path, arc_name)
            
            # Add migration guide
            conversion_result = session.get('conversion_result', {})
            migration_guide = conversion_result.get('migration_guide', '')
            
            if migration_guide:
                zip_file.writestr('MIGRATION_GUIDE.md', migration_guide)
            
            # Add summary
            summary = conversion_result.get('summary', {})
            if summary:
                import json
                zip_file.writestr('conversion_summary.json', 
                                json.dumps(summary, indent=2))
        
        zip_buffer.seek(0)
        
        # Get target framework for filename
        target_framework = session.get('target_framework', 'converted')
        filename = f'{target_framework}_project_{project_id[:8]}.zip'
        
        current_app.logger.info(f"Sending ZIP file: {filename}")
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        current_app.logger.error(f"Download error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Download failed: {str(e)}'
        }), 500

@download_bp.route('/download/<project_id>/migration-guide', methods=['GET'])
def download_migration_guide(project_id):
    """
    Download only the migration guide
    
    Response:
        Markdown file
    """
    
    try:
        # Verify project
        session_project_id = session.get('project_id')
        
        if session_project_id != project_id:
            return jsonify({
                'status': 'error',
                'message': 'Invalid project ID'
            }), 403
        
        # Get migration guide from session
        conversion_result = session.get('conversion_result', {})
        migration_guide = conversion_result.get('migration_guide', '')
        
        if not migration_guide:
            return jsonify({
                'status': 'error',
                'message': 'Migration guide not found'
            }), 404
        
        # Create file buffer
        buffer = io.BytesIO(migration_guide.encode('utf-8'))
        buffer.seek(0)
        
        filename = f'migration_guide_{project_id[:8]}.md'
        
        return send_file(
            buffer,
            mimetype='text/markdown',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        current_app.logger.error(f"Migration guide download error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Download failed: {str(e)}'
        }), 500

@download_bp.route('/cleanup/<project_id>', methods=['DELETE'])
def cleanup_project(project_id):
    """
    Manual cleanup of project files
    
    Response:
        {
            "status": "success",
            "message": "Project files cleaned up"
        }
    """
    
    try:
        # Verify project
        session_project_id = session.get('project_id')
        
        if session_project_id != project_id:
            return jsonify({
                'status': 'error',
                'message': 'Invalid project ID'
            }), 403
        
        # Get project path
        project_path = session.get('project_path')
        
        if project_path and os.path.exists(project_path):
            # Cleanup files
            file_manager = FileManager(current_app.config['UPLOAD_FOLDER'])
            file_manager.cleanup_project(project_path)
            
            current_app.logger.info(f"Project cleaned up: {project_id}")
        
        # Clear session
        session.clear()
        
        return jsonify({
            'status': 'success',
            'message': 'Project files cleaned up successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Cleanup error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Cleanup failed: {str(e)}'
        }), 500