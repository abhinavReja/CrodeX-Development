from flask import Blueprint, request, jsonify, session, current_app, render_template, redirect, url_for, flash
from schemas.conversion_schema import ConversionValidator
from middleware.validation import validate_request
from services.converter import ProjectConverter
from datetime import datetime
import threading
import os

conversion_bp = Blueprint('conversion', __name__)

# Template route for progress page (no prefix)
def progress_page(project_id):
    """
    Display progress page and optionally start conversion
    Note: This route is registered without /api prefix in app.py
    """
    # Verify project belongs to session
    session_project_id = session.get('project_id')
    
    if session_project_id != project_id:
        flash('Invalid project ID or session expired. Please upload a file first.', 'error')
        return redirect(url_for('upload.upload'))
    
    # Check if conversion should be started
    context = session.get('project_context')
    if context and context.get('target_framework') and not session.get('conversion_complete'):
        # Auto-start conversion if context is confirmed and conversion hasn't started
        if not session.get('conversion_progress'):
            # Start conversion in background (non-blocking)
            # For now, we'll let the frontend call the API to start conversion
            pass
    
    # Render progress page
    return render_template('progress.html', project_id=project_id)

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
        
        # Validate session data - files_dict and context are required, analysis is optional
        if not project_id:
            return jsonify({
                'status': 'error',
                'message': 'No active project found. Please upload a file first.'
            }), 400
        
        if not files_dict:
            return jsonify({
                'status': 'error',
                'message': 'Project files not found. Please upload a file first.'
            }), 400
        
        if not context:
            return jsonify({
                'status': 'error',
                'message': 'Project context not found. Please complete the context form first before starting conversion.'
            }), 400
        
        # Analysis is optional - if not present, perform quick local analysis
        if not analysis:
            current_app.logger.warning(f"No analysis found for project {project_id}, performing quick analysis")
            try:
                from services.analyzer import FrameworkAnalyzer
                analyzer = FrameworkAnalyzer()
                local_analysis = analyzer.analyze_structure(files_dict)
                
                # Store basic analysis in session
                analysis = {
                    'framework': local_analysis.get('primary_framework', 'Unknown'),
                    'confidence': local_analysis.get('confidence', 0),
                    'structure': local_analysis.get('structure', {}),
                    'dependencies': local_analysis.get('dependencies', []),
                    'database': local_analysis.get('database', {}),
                    'file_stats': local_analysis.get('file_stats', {}),
                    'notes': local_analysis.get('notes', '')
                }
                session['analysis'] = analysis
                session.modified = True
                current_app.logger.info(f"Quick analysis completed: {analysis.get('framework')}")
            except Exception as e:
                current_app.logger.warning(f"Quick analysis failed: {str(e)}")
                # Continue without analysis - converter will do analysis
        
        # Get target framework from request or session context
        data = request.get_json() if request.is_json else {}
        target_framework = data.get('target_framework') or context.get('target_framework') or context.get('target-framework')
        
        if not target_framework:
            current_app.logger.error(f"Target framework missing for project {project_id}. Context keys: {list(context.keys()) if context else 'No context'}")
            return jsonify({
                'status': 'error',
                'message': 'Target framework is required. Please provide it in the context form. Make sure you select a target framework before starting conversion.',
                'details': {
                    'context_available': bool(context),
                    'context_keys': list(context.keys()) if context else [],
                    'request_data': data
                }
            }), 400
        
        # Initialize converter - use GEMINI_API_KEY from config or environment
        api_key = current_app.config.get('GEMINI_API_KEY') or current_app.config.get('ANTHROPIC_API_KEY') or os.getenv('GEMINI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({
                'status': 'error',
                'message': 'API key not configured. Please set GEMINI_API_KEY or ANTHROPIC_API_KEY environment variable.'
            }), 500
        
        converter = ProjectConverter(api_key)
        
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
        
        # Store conversion results in session (only summary, not full file contents to avoid cookie size limits)
        # Store a lightweight summary instead of the full conversion_result
        session['conversion_result'] = {
            'source_framework': conversion_result.get('source_framework'),
            'target_framework': target_framework,
            'files_converted': len(conversion_result.get('converted_files', [])),
            'summary': conversion_result.get('summary', {}),
            # Don't store full converted_files list to avoid session cookie size issues
        }
        session['conversion_complete'] = True
        session['conversion_progress'] = 100
        session['target_framework'] = target_framework
        session['conversion_timestamp'] = datetime.now().isoformat()
        session.modified = True
        
        # Convert list of converted files to dictionary format
        # converted_files is a list of dicts with keys: original_path, converted_code, new_file_path, etc.
        converted_files_list = conversion_result.get('converted_files', [])
        converted_files_dict = {}
        skipped_files = []
        
        for file_info in converted_files_list:
            # Skip files with errors
            if file_info.get('error'):
                error_msg = file_info.get('error', 'Unknown error')
                original_path = file_info.get('original_path', 'unknown')
                current_app.logger.warning(f"Skipping file with error: {original_path} - {error_msg}")
                skipped_files.append({'path': original_path, 'error': error_msg})
                continue
            
            # Get file path (prefer new_file_path, fallback to original_path)
            file_path = file_info.get('new_file_path') or file_info.get('original_path')
            if not file_path:
                current_app.logger.warning(f"Skipping file without path: {file_info}")
                skipped_files.append({'path': 'unknown', 'error': 'No file path provided'})
                continue
            
            # Normalize file path (remove leading slashes, handle Windows paths)
            file_path = file_path.lstrip('/\\').replace('\\', '/')
            
            # Get file content (converted_code)
            file_content = file_info.get('converted_code')
            if file_content is None or file_content == '':
                current_app.logger.warning(f"Skipping file without content: {file_path}")
                skipped_files.append({'path': file_path, 'error': 'No converted code available'})
                continue
            
            # Store file path and content
            converted_files_dict[file_path] = file_content
        
        # Log summary
        current_app.logger.info(f"Converted {len(converted_files_dict)} files successfully, skipped {len(skipped_files)} files")
        if skipped_files:
            current_app.logger.warning(f"Skipped files: {[f['path'] for f in skipped_files]}")
        
        # Save converted files to disk
        from utils.file_manager import FileManager
        file_manager = FileManager(current_app.config['UPLOAD_FOLDER'])
        
        project_path = session.get('project_path')
        
        if not converted_files_dict:
            current_app.logger.warning("No converted files to save")
            # Still create the converted directory for consistency
            from pathlib import Path
            converted_path = Path(project_path) / 'converted'
            converted_path.mkdir(parents=True, exist_ok=True)
        else:
            converted_path = file_manager.save_converted_files(
                project_path,
                converted_files_dict
            )
        
        session['converted_path'] = str(converted_path)  # Convert Path to string
        session.modified = True
        
        current_app.logger.info(f"Conversion completed: {project_id}")
        
        # Get file count from saved files
        files_converted_count = len(converted_files_dict) if converted_files_dict else 0
        warnings_count = conversion_result.get('summary', {}).get('conversion_stats', {}).get('total_warnings', 0)
        
        return jsonify({
            'status': 'success',
            'project_id': project_id,
            'conversion': {
                'source_framework': conversion_result['source_framework'],
                'target_framework': target_framework,
                'files_converted': files_converted_count,
                'warnings': warnings_count,
                'download_url': f'/api/download/{project_id}'
            },
            'summary': conversion_result.get('summary', {})
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