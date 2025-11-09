# filepath: routes/download_routes.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_file, session, current_app
from utils.file_manager import FileManager
from pathlib import Path

download_bp = Blueprint('download', __name__)
api_download_bp = Blueprint('api_download', __name__)

@download_bp.route('/download/<project_id>', methods=['GET'])
def download_file(project_id):
    """Web download page"""
    try:
        if session.get('project_id') != project_id:
            flash('Invalid project ID or session expired.', 'error')
            return redirect(url_for('upload.upload'))

        converted_path = session.get('converted_path')
        if not converted_path:
            flash('Conversion not completed yet.', 'error')
            return redirect(url_for('conversion.progress_page', project_id=project_id))

        fm = FileManager(current_app.config['UPLOAD_FOLDER'])
        converted_path_obj = Path(converted_path)
        if not converted_path_obj.exists():
            flash('Converted files not found.', 'error')
            return redirect(url_for('upload.upload'))

        if request.args.get('download') == 'true':
            zip_path = fm.create_download_zip(converted_path)
            return send_file(
                str(zip_path),
                mimetype='application/zip',
                as_attachment=True,
                download_name=f'converted_{project_id}.zip'
            )

        conversion_result = session.get('conversion_result', {})
        return render_template(
            'download.html',
            project_id=project_id,
            original_name=session.get('original_filename', 'project.zip'),
            processed_name=f'converted_{project_id}.zip',
            files_processed=conversion_result.get('files_converted', 0)
        )
    except Exception as e:
        current_app.logger.error(f"Download error: {e}")
        flash(f"Error: {e}", 'error')
        return redirect(url_for('upload.upload'))


@api_download_bp.route('/download/<project_id>', methods=['GET'])
def download_file_content(project_id):
    """API endpoint used by progress.html’s ‘download’ button"""
    try:
        if session.get('project_id') != project_id:
            return jsonify({'error': 'Invalid project ID'}), 403

        converted_path = session.get('converted_path')
        if not converted_path:
            return jsonify({'error': 'Conversion not completed yet'}), 400

        fm = FileManager(current_app.config['UPLOAD_FOLDER'])
        zip_path = fm.create_download_zip(converted_path)
        return send_file(
            str(zip_path),
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'converted_{project_id}.zip'
        )
    except Exception as e:
        current_app.logger.exception("API download failed")
        return jsonify({'error': f'Error creating download file: {str(e)}'}), 500
