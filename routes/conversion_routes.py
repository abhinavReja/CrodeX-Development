# filepath: routes/conversion_routes.py
from flask import Blueprint, request, jsonify, session, current_app, render_template, redirect, url_for, flash
from schemas.conversion_schema import ConversionValidator
from middleware.validation import validate_request
from services.converter import ProjectConverter
from datetime import datetime
from pathlib import Path
import os
import json

conversion_bp = Blueprint('conversion', __name__)

# --- helpers -------------------------------------------------------
def _ensure_dict(x):
    if isinstance(x, dict):
        return x
    if isinstance(x, str):
        try:
            return json.loads(x)
        except Exception:
            return {"summary": x}
    return {"summary": str(x)}

def _ensure_list_of_dicts(items):
    out = []
    for it in (items or []):
        if isinstance(it, dict):
            out.append(it)
        elif isinstance(it, str):
            try:
                out.append(json.loads(it))
            except Exception:
                out.append({"converted_code": None, "error": "non-json item", "raw": it})
        else:
            out.append({"converted_code": None, "error": "unexpected type", "raw_type": str(type(it))})
    return out
# -------------------------------------------------------------------

def progress_page(project_id):
    """Render existing progress.html template"""
    return render_template('progress.html', project_id=project_id)


@conversion_bp.route('/convert', methods=['POST'])
@validate_request(ConversionValidator)
def convert_project():
    """Main conversion endpoint"""
    # LOG IMMEDIATELY when endpoint is hit
    current_app.logger.info("=" * 80)
    current_app.logger.info("CONVERSION ENDPOINT HIT - /api/convert")
    current_app.logger.info("=" * 80)
    
    try:
        project_id = session.get('project_id')
        files_dict = session.get('files_dict')
        analysis = session.get('analysis')
        context = session.get('project_context')
        session_project_path = session.get('project_path')
        
        current_app.logger.info(f"Session data - project_id: {project_id}, files_dict: {len(files_dict) if files_dict else 0}, context: {bool(context)}")

        # CRITICAL: Validate session data and verify project_id matches
        if not project_id:
            current_app.logger.error("No project_id in session")
            return jsonify({'status': 'error', 'message': 'No project ID found. Please upload a project first.'}), 400
        
        if not files_dict:
            current_app.logger.error(f"No files_dict in session for project {project_id}")
            return jsonify({'status': 'error', 'message': 'No files found in session. Please upload a project first.'}), 400
        
        if not context:
            current_app.logger.error(f"No project_context in session for project {project_id}")
            return jsonify({'status': 'error', 'message': 'Session missing context. Please confirm project context again.'}), 400
        
        # Verify files_dict is not empty
        if not isinstance(files_dict, dict) or len(files_dict) == 0:
            current_app.logger.error(f"files_dict is empty or invalid for project {project_id}: type={type(files_dict)}, len={len(files_dict) if isinstance(files_dict, dict) else 'N/A'}")
            
            # Try to reload files from disk as fallback
            extracted_path = session.get('extracted_path')
            if extracted_path:
                current_app.logger.warning(f"Attempting to reload files from disk: {extracted_path}")
                try:
                    from utils.file_manager import FileManager
                    fm = FileManager(current_app.config['UPLOAD_FOLDER'])
                    files_dict = fm.load_files(extracted_path)
                    session['files_dict'] = files_dict
                    session.modified = True
                    current_app.logger.info(f"Reloaded {len(files_dict)} files from disk")
                except Exception as e:
                    current_app.logger.error(f"Failed to reload files from disk: {e}")
                    return jsonify({'status': 'error', 'message': 'Uploaded project contains no files. Please upload a valid project.'}), 400
            else:
                return jsonify({'status': 'error', 'message': 'Uploaded project contains no files. Please upload a valid project.'}), 400
        
        current_app.logger.info(f"Conversion request for project {project_id} with {len(files_dict)} files")
        
        # Log a hash of file names to verify uniqueness
        file_names_hash = hash(tuple(sorted(files_dict.keys())))
        current_app.logger.info(f"Files hash: {file_names_hash} (first 10 files: {list(files_dict.keys())[:10]})")

        target_framework = (
            request.get_json(silent=True) or {}
        ).get('target_framework') or context.get('target_framework') or 'Spring Boot'

        # Detect source framework to determine if API key is needed
        from services.analyzer import FrameworkAnalyzer
        analyzer = FrameworkAnalyzer()
        source_fw_detected = analyzer.analyze_structure(files_dict).get('primary_framework', 'Unknown')
        
        # API key only needed for non-Flask projects or non-Spring Boot targets
        # Flask → Spring Boot uses fast deterministic converter (no API key needed)
        use_gemini = not (
            source_fw_detected.lower() == "flask" and 
            target_framework.lower() in ("spring boot", "spring-boot", "springboot")
        )
        
        api_key = None
        if use_gemini:
            api_key = (
                current_app.config.get('GEMINI_API_KEY')
                or current_app.config.get('ANTHROPIC_API_KEY')
                or os.getenv('GEMINI_API_KEY')
                or os.getenv('ANTHROPIC_API_KEY')
            )
            if not api_key:
                current_app.logger.warning(f"API key not configured, but needed for {source_fw_detected} → {target_framework}")
                return jsonify({
                    'status': 'error', 
                    'message': f'API key required for {source_fw_detected} → {target_framework} conversion. Please configure GEMINI_API_KEY.'
                }), 500
        else:
            current_app.logger.info(f"Using fast deterministic converter for {source_fw_detected} → {target_framework} (no API key needed)")

        converter = ProjectConverter()

        def progress_callback(*args):
            # Handle different callback signatures:
            # - (stage, message) from Flask converter
            # - (current, total, file_path) from GeminiService
            # - (stage, message) fallback from GeminiService
            try:
                if len(args) == 2:
                    # Standard format: (stage, message)
                    stage, message = args
                    session['conversion_stage'] = stage
                    session['conversion_message'] = message
                    stage_progress = {'analysis': 10, 'conversion': 70, 'documentation': 90, 'complete': 100}
                    session['conversion_progress'] = stage_progress.get(stage, 0)
                elif len(args) == 3:
                    # GeminiService format: (current, total, file_path)
                    current, total, file_path = args
                    percentage = int((current / total) * 70) + 10  # 10-80% range for conversion
                    session['conversion_stage'] = 'conversion'
                    session['conversion_message'] = f"Converting {current}/{total}: {file_path}"
                    session['conversion_progress'] = percentage
                else:
                    # Unknown format, try to handle gracefully
                    session['conversion_message'] = str(args[0]) if args else "Processing..."
                
                session.modified = True
                current_app.logger.info(f"Progress update: {args}")
            except Exception as e:
                current_app.logger.error(f"Error in progress_callback: {e}")
                # Don't let callback errors break conversion

        # CRITICAL: Log what files we're actually converting
        current_app.logger.info(f"Starting conversion: {project_id} → {target_framework}")
        current_app.logger.info(f"Files dict type: {type(files_dict)}, length: {len(files_dict) if files_dict else 0}")
        if files_dict:
            file_keys = list(files_dict.keys())[:10]  # First 10 files
            current_app.logger.info(f"Sample files being converted: {file_keys}")
            # Check file types
            py_files = [f for f in file_keys if f.endswith('.py')]
            js_files = [f for f in file_keys if f.endswith('.js')]
            html_files = [f for f in file_keys if f.endswith('.html')]
            current_app.logger.info(f"File types - Python: {len(py_files)}, JS: {len(js_files)}, HTML: {len(html_files)}")
        else:
            current_app.logger.error("ERROR: files_dict is empty or None!")
            return jsonify({'status': 'error', 'message': 'No files found to convert. Please upload a project first.'}), 400
        
        # Initialize progress BEFORE starting conversion
        try:
            progress_callback("analysis", "Starting conversion...")
            session.modified = True
        except Exception as e:
            current_app.logger.warning(f"Progress callback failed: {e}")
        
        try:
            current_app.logger.info("=" * 80)
            current_app.logger.info("CALLING converter.full_conversion_pipeline NOW")
            current_app.logger.info(f"Files: {len(files_dict)}, Target: {target_framework}")
            current_app.logger.info("=" * 80)
            
            raw_result = converter.full_conversion_pipeline(
                files=files_dict,
                target_framework=target_framework,
                project_context={**context, "api_key": api_key} if api_key else context,
                progress_callback=progress_callback,
                api_key=api_key
            )
            
            current_app.logger.info("=" * 80)
            current_app.logger.info("Converter returned successfully")
            current_app.logger.info(f"Result type: {type(raw_result)}, keys: {list(raw_result.keys()) if isinstance(raw_result, dict) else 'N/A'}")
            current_app.logger.info("=" * 80)
        except Exception as conv_error:
            current_app.logger.exception(f"Conversion pipeline raised exception: {conv_error}")
            try:
                progress_callback("error", f"Conversion failed: {str(conv_error)}")
            except:
                pass
            session['conversion_error'] = str(conv_error)
            session['conversion_stage'] = 'error'
            session['conversion_message'] = f"Error: {str(conv_error)}"
            session.modified = True
            raise

        result = _ensure_dict(raw_result)
        converted_files = _ensure_list_of_dicts(result.get('converted_files', []))
        summary = result.get('summary', {}) if isinstance(result.get('summary'), dict) else {"summary_text": str(result.get('summary'))}

        # Log conversion results
        current_app.logger.info(f"Conversion complete: {len(converted_files)} files generated")
        if converted_files:
            sample_output = [cf.get('new_file_path', 'unknown') for cf in converted_files[:10]]
            current_app.logger.info(f"Sample converted files: {sample_output}")
            
            # Verify critical files are present
            file_paths = [cf.get('new_file_path', '') for cf in converted_files]
            critical_files = ["pom.xml", "src/main/java/com/example/demo/DemoApplication.java", "README.md"]
            missing = [f for f in critical_files if f not in file_paths]
            if missing:
                current_app.logger.error(f"CRITICAL: Missing required files in converter output: {missing}")
            
            # Verify controller exists
            has_controller = any('Controller' in path for path in file_paths)
            if not has_controller:
                current_app.logger.error("CRITICAL: No controller found in converter output!")
        else:
            current_app.logger.error("CRITICAL: Converter returned empty file list!")
            return jsonify({
                'status': 'error',
                'message': 'Conversion failed: No files were generated. Please check the logs.'
            }), 500

        from utils.file_manager import FileManager
        fm = FileManager(current_app.config['UPLOAD_FOLDER'])
        project_path = session.get('project_path')
        
        # Verify we're using the correct project path
        if not project_path or project_path != session_project_path:
            current_app.logger.error(f"Project path mismatch: session has {session_project_path}, using {project_path}")
        
        converted_path = fm.save_converted_files(project_path, converted_files)
        
        # Verify files were saved
        converted_path_obj = Path(converted_path)
        if converted_path_obj.exists():
            saved_files = [f for f in converted_path_obj.rglob('*') if f.is_file()]
            current_app.logger.info(f"Saved {len(saved_files)} files to {converted_path}")
        else:
            current_app.logger.error(f"Converted path does not exist: {converted_path}")

        session['converted_path'] = str(converted_path)
        session['conversion_result'] = {
            'source_framework': result.get('source_framework', analysis.get('framework') if analysis else None),
            'target_framework': target_framework,
            'files_converted': len(converted_files),
            'summary': summary
        }
        # ✅ Mark conversion as complete
        session['conversion_complete'] = True
        session['conversion_progress'] = 100
        session['target_framework'] = target_framework
        session['conversion_timestamp'] = datetime.now().isoformat()
        session.modified = True
        current_app.logger.info(f"✅ Conversion complete for {project_id}")

        return jsonify({
            'status': 'success',
            'project_id': project_id,
            'conversion': {
                'source_framework': result.get('source_framework'),
                'target_framework': target_framework,
                'files_converted': len(converted_files),
                'download_url': f'/api/download/{project_id}'
            },
            'summary': summary
        }), 200

    except Exception as e:
        current_app.logger.exception("Conversion error")
        session['conversion_error'] = str(e)
        session.modified = True
        return jsonify({'status': 'error', 'message': f'Conversion failed: {str(e)}'}), 500


@conversion_bp.route('/conversion-progress/<project_id>', methods=['GET'])
def get_conversion_progress(project_id):
    """AJAX progress endpoint used by progress.html polling"""
    try:
        if session.get('project_id') != project_id:
            return jsonify({'status': 'error', 'message': 'Invalid project ID'}), 403

        progress = {
            'percentage': session.get('conversion_progress', 0),
            'stage': session.get('conversion_stage', 'pending'),
            'message': session.get('conversion_message', 'Waiting to start'),
            'complete': bool(session.get('conversion_complete')),
            'error': session.get('conversion_error')
        }
        
        # Log progress for debugging
        current_app.logger.debug(f"Progress check for {project_id}: {progress['percentage']}% - {progress['stage']} - {progress['message']}")
        
        return jsonify({'status': 'success', 'progress': progress}), 200
    except Exception as e:
        current_app.logger.error(f"Progress check error: {e}")
        return jsonify({'status': 'error', 'message': f'Progress check failed: {e}'}), 500
