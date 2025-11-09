from flask import Blueprint, request, jsonify, session, current_app
from schemas.conversion_schema import ConversionValidator
from middleware.validation import validate_request
from services.converter import ProjectConverter
from datetime import datetime

conversion_bp = Blueprint('conversion', __name__)

@conversion_bp.route('/convert', methods=['POST'])
@validate_request(ConversionValidator)
def convert_project():
    """
    Convert project to target framework
    
    Request:
        {
            "target_framework": "Django"
        }
        
    Response:
        {
            "status": "success",
            "project_id": "uuid",
            "conversion": {
                "files_converted": 45,
                "warnings": 3,
                "download_url": "/api/download/uuid"
            }
        }
    """
    
    try:
        # Get project data from session
        project_id = session.get('project_id')
        files_dict = session.get('files_dict')
        analysis = session.get('analysis')
        context = session.get('project_context')
        
        # Validate session data
        if not all([project_id, files_dict, analysis, context]):
            return jsonify({
                'status': 'error',
                'message': 'Missing project data. Please complete upload and analysis first.'
            }), 400
        
        # Get target framework from request
        data = request.get_json()
        target_framework = data['target_framework']
        
        # Initialize converter
        converter = ProjectConverter(current_app.config['ANTHROPIC_API_KEY'])
        
        # Progress tracking function
        def progress_callback(stage, message):
            session['conversion_stage'] = stage
            session['conversion_message'] = message
            
            # Calculate progress percentage
            stage_progress = {
                'analysis': 10,
                'conversion': 70,
                'documentation': 90
            }
            session['conversion_progress'] = stage_progress.get(stage, 0)
            session.modified = True
            
            current_app.logger.info(f"Conversion progress - {stage}: {message}")
        
        # Start conversion
        current_app.logger.info(f"Starting conversion: {project_id} -> {target_framework}")
        
        conversion_result = converter.full_conversion_pipeline(
            files=files_dict,
            target_framework=target_framework,
            project_context=context,
            progress_callback=progress_callback
        )
        
        # Store conversion results in session
        session['conversion_result'] = conversion_result
        session['conversion_complete'] = True
        session['conversion_progress'] = 100
        session['target_framework'] = target_framework
        session['conversion_timestamp'] = datetime.now().isoformat()
        session.modified = True
        
        # Save converted files to disk
        from utils.file_manager import FileManager
        file_manager = FileManager(current_app.config['UPLOAD_FOLDER'])
        
        project_path = session.get('project_path')
        converted_path = file_manager.save_converted_files(
            project_path,
            conversion_result['converted_files']
        )
        
        session['converted_path'] = converted_path
        session.modified = True
        
        current_app.logger.info(f"Conversion completed: {project_id}")
        
        return jsonify({
            'status': 'success',
            'project_id': project_id,
            'conversion': {
                'source_framework': conversion_result['source_framework'],
                'target_framework': target_framework,
                'files_converted': len(conversion_result['converted_files']),
                'warnings': conversion_result['summary']['conversion_stats']['total_warnings'],
                'download_url': f'/api/download/{project_id}'
            },
            'summary': conversion_result['summary']
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Conversion error: {str(e)}")
        
        # Store error in session
        session['conversion_error'] = str(e)
        session.modified = True
        
        return jsonify({
            'status': 'error',
            'message': f'Conversion failed: {str(e)}'
        }), 500

@conversion_bp.route('/conversion-progress/<project_id>', methods=['GET'])
def get_conversion_progress(project_id):
    """
    Get real-time conversion progress
    
    Response:
        {
            "status": "success",
            "progress": {
                "percentage": 65,
                "stage": "conversion",
                "message": "Converting file 30/45"
            }
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
        
        # Get progress from session
        progress = {
            'percentage': session.get('conversion_progress', 0),
            'stage': session.get('conversion_stage', 'pending'),
            'message': session.get('conversion_message', 'Waiting to start'),
            'complete': session.get('conversion_complete', False),
            'error': session.get('conversion_error')
        }
        
        return jsonify({
            'status': 'success',
            'progress': progress
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Progress check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Progress check failed: {str(e)}'
        }), 500