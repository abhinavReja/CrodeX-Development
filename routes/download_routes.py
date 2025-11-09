from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_file, session, current_app
from utils.file_manager import FileManager

download_bp = Blueprint('download', __name__)
api_download_bp = Blueprint('api_download', __name__)

@download_bp.route('/download/<project_id>', methods=['GET'])
def download_file(project_id):
    """Download page and file download"""
    try:
        # Verify project belongs to session
        session_project_id = session.get('project_id')
        
        if session_project_id != project_id:
            current_app.logger.warning(f"Download route: Session project_id {session_project_id} != requested {project_id}")
            flash('Invalid project ID or session expired. Please upload a file first.', 'error')
            return redirect(url_for('upload.upload'))
        
        # Get project data from session
        converted_path = session.get('converted_path')
        conversion_result = session.get('conversion_result', {})
        
        current_app.logger.info(f"Download route accessed for project {project_id}, converted_path: {converted_path}")
        
        if not converted_path:
            current_app.logger.warning(f"Download route: No converted_path in session for project {project_id}")
            flash('Conversion not completed yet. Please wait for conversion to finish.', 'error')
            return redirect(url_for('conversion.progress_page', project_id=project_id))
        
        # Verify converted_path exists on disk
        from pathlib import Path
        converted_path_obj = Path(converted_path)
        if not converted_path_obj.exists():
            current_app.logger.error(f"Download route: Converted path does not exist: {converted_path}")
            flash('Converted files not found. Please restart the conversion.', 'error')
            return redirect(url_for('upload.upload'))
    
        # Get file information
        file_manager = FileManager(current_app.config['UPLOAD_FOLDER'])
        
        # Get file count from conversion result (stored as count, not full list)
        files_processed = conversion_result.get('files_converted', 0)
        
        # Get original filename from session
        original_filename = session.get('original_filename', 'project.zip')
        
        # If it's a download request (with download parameter)
        if request.args.get('download') == 'true':
            # Create ZIP file for download
            try:
                zip_path = file_manager.create_download_zip(converted_path)
                current_app.logger.info(f"Created download ZIP: {zip_path} for project {project_id}")
                return send_file(
                    str(zip_path),
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name=f'converted_{project_id}.zip'
                )
            except Exception as e:
                current_app.logger.error(f"Error creating download ZIP: {str(e)}")
                flash('Error creating download file', 'error')
                return redirect(url_for('download.download_file', project_id=project_id))
        
        # Show download page
        return render_template('download.html', 
                             file_id=project_id,  # Use project_id as file_id for template compatibility
                             project_id=project_id,
                             original_name=original_filename,
                             processed_name=f'converted_{project_id}.zip',
                             file_size=0,  # Will be calculated if needed
                             files_processed=files_processed)
    
    except Exception as e:
        current_app.logger.error(f"Download route error: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash(f'Error accessing download page: {str(e)}', 'error')
        return redirect(url_for('upload.upload'))

# API routes (registered with /api prefix)
@api_download_bp.route('/download/<project_id>', methods=['GET'])
def download_file_content(project_id):
    """Download the actual file - API route"""
    try:
        # Verify project belongs to session
        session_project_id = session.get('project_id')
        
        if session_project_id != project_id:
            current_app.logger.warning(f"API Download: Session project_id {session_project_id} != requested {project_id}")
            return jsonify({'error': 'Invalid project ID'}), 403
        
        # Get converted path from session
        converted_path = session.get('converted_path')
        
        if not converted_path:
            current_app.logger.warning(f"API Download: No converted_path in session for project {project_id}")
            return jsonify({'error': 'Conversion not completed yet'}), 400
        
        # Verify converted_path exists on disk
        from pathlib import Path
        converted_path_obj = Path(converted_path)
        if not converted_path_obj.exists():
            current_app.logger.error(f"API Download: Converted path does not exist: {converted_path}")
            return jsonify({'error': 'Converted files not found. Please restart the conversion.'}), 404
        
        # Create ZIP file for download
        file_manager = FileManager(current_app.config['UPLOAD_FOLDER'])
        zip_path = file_manager.create_download_zip(converted_path)
        
        current_app.logger.info(f"API Download: Created ZIP {zip_path} for project {project_id}")
        
        return send_file(
            str(zip_path),
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'converted_{project_id}.zip'
        )
    except Exception as e:
        current_app.logger.error(f"Error creating download ZIP: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Error creating download file: {str(e)}'}), 500
