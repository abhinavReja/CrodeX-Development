from flask import Blueprint, request, jsonify, session, current_app, render_template, redirect, url_for, flash
from schemas.context_schema import ContextValidator
from middleware.validation import validate_request
from services.gemini_api import GeminiService
from services.analyzer import FrameworkAnalyzer
from datetime import datetime
import os

analysis_bp = Blueprint('analysis', __name__)

# Template route for context form (no prefix, so it's accessible as /context/<project_id>)
def context_form(project_id):
    """
    Display context form page (template route) - handles both GET and POST
    Note: This route is registered without /api prefix in app.py
    """
    # Verify project belongs to session
    session_project_id = session.get('project_id')
    
    if session_project_id != project_id:
        flash('Invalid project ID or session expired. Please upload a file first.', 'error')
        return redirect(url_for('upload.upload'))
    
    # Handle POST request (form submission)
    if request.method == 'POST':
        try:
            # Get context from request
            if request.is_json:
                context_data = request.get_json()
            else:
                # Handle form data
                context_data = {
                    'purpose': request.form.get('purpose', ''),
                    'features': request.form.getlist('features') if hasattr(request.form, 'getlist') else [],
                    'business_logic': request.form.get('business-logic', ''),
                    'requirements': request.form.getlist('requirements') if hasattr(request.form, 'getlist') else [],
                    'target_framework': request.form.get('target-framework', '')
                }
            
            # Validate required fields
            required_fields = ['purpose', 'features', 'business_logic']
            for field in required_fields:
                if field not in context_data or not context_data[field]:
                    if request.is_json:
                        return jsonify({
                            'status': 'error',
                            'message': f'Missing required field: {field}'
                        }), 400
                    else:
                        flash(f'Missing required field: {field}', 'error')
                        return render_template('context_form.html', file_id=project_id, project_id=project_id)
            
            # Store context in session
            session['project_context'] = {
                'purpose': context_data.get('purpose', ''),
                'features': context_data.get('features', []) if isinstance(context_data.get('features', []), list) else [context_data.get('features', '')],
                'business_logic': context_data.get('business_logic', ''),
                'requirements': context_data.get('requirements', []),
                'target_framework': context_data.get('target_framework') or context_data.get('target-framework'),  # Support both formats
                'confirmed_at': datetime.now().isoformat()
            }
            session.modified = True
            
            # Log stored context for debugging
            current_app.logger.info(f"Context stored for project {project_id}: target_framework={session['project_context'].get('target_framework')}")
            
            current_app.logger.info(f"Context confirmed for project: {project_id}")
            
            # Return JSON response for AJAX requests
            if request.is_json:
                # Redirect to progress page (which will start conversion)
                redirect_url = url_for('conversion.progress_page', project_id=project_id)
                return jsonify({
                    'status': 'success',
                    'message': 'Context confirmed successfully',
                    'project_id': project_id,
                    'redirect_url': redirect_url
                }), 200
            else:
                # Redirect for form submission
                return redirect(url_for('conversion.progress_page', project_id=project_id))
                
        except Exception as e:
            current_app.logger.error(f"Context confirmation error: {str(e)}")
            if request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': f'Context confirmation failed: {str(e)}'
                }), 500
            else:
                flash(f'Error: {str(e)}', 'error')
                return render_template('context_form.html', file_id=project_id, project_id=project_id)
    
    # Handle GET request - render context form template
    # Pass project_id as file_id for template compatibility
    return render_template('context_form.html', file_id=project_id, project_id=project_id)

@analysis_bp.route('/analyze', methods=['POST'])
def analyze_project():
    """
    Analyze uploaded project to detect framework
    
    Response:
        {
            "status": "success",
            "project_id": "uuid",
            "analysis": {
                "framework": "Laravel",
                "confidence": 95,
                "structure": {...},
                "suggestions": [...]
            }
        }
    """
    
    try:
        # Get project from session
        project_id = session.get('project_id')
        files_dict = session.get('files_dict')
        
        if not project_id or not files_dict:
            return jsonify({
                'status': 'error',
                'message': 'No project found. Please upload a project first.'
            }), 400
        
        # Initialize analyzer
        analyzer = FrameworkAnalyzer()
        
        # Step 1: Quick local analysis (always performed)
        current_app.logger.info(f"Starting local analysis for {project_id}")
        local_analysis = analyzer.analyze_structure(files_dict)
        
        # Step 2: Try AI analysis if API key is available (optional enhancement)
        api_key = current_app.config.get('GEMINI_API_KEY') or current_app.config.get('ANTHROPIC_API_KEY') or os.getenv('GEMINI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        
        if api_key:
            try:
                current_app.logger.info(f"Starting AI analysis for {project_id}")
                gemini_service = GeminiService(api_key)
                ai_analysis = gemini_service.analyze_project_structure(files_dict)
                
                # Combine results (prefer AI analysis, fallback to local)
                combined_analysis = {
                    'framework': ai_analysis.get('framework') or local_analysis.get('framework') or local_analysis.get('primary_framework', 'Unknown'),
                    'confidence': ai_analysis.get('confidence', local_analysis.get('confidence', 0)),
                    'structure': ai_analysis.get('structure', local_analysis.get('structure', {})),
                    'dependencies': ai_analysis.get('dependencies', local_analysis.get('dependencies', [])),
                    'database': ai_analysis.get('database', local_analysis.get('database', {})),
                    'file_stats': local_analysis.get('file_stats', {}),
                    'notes': ai_analysis.get('notes', '') or local_analysis.get('notes', ''),
                    'business_logic': ai_analysis.get('business_logic', '')  # Include business logic from AI analysis
                }
            except Exception as e:
                current_app.logger.warning(f"AI analysis failed, using local analysis: {str(e)}")
                # Fallback to local analysis only
                combined_analysis = {
                    'framework': local_analysis.get('framework') or local_analysis.get('primary_framework', 'Unknown'),
                    'confidence': local_analysis.get('confidence', 0),
                    'structure': local_analysis.get('structure', {}),
                    'dependencies': local_analysis.get('dependencies', []),
                    'database': local_analysis.get('database', {}),
                    'file_stats': local_analysis.get('file_stats', {}),
                    'notes': local_analysis.get('notes', ''),
                    'business_logic': ''  # Empty business logic for local analysis only
                }
        else:
            # No API key, use local analysis only
            current_app.logger.info(f"Using local analysis only (no API key) for {project_id}")
            combined_analysis = {
                'framework': local_analysis.get('framework') or local_analysis.get('primary_framework', 'Unknown'),
                'confidence': local_analysis.get('confidence', 0),
                'structure': local_analysis.get('structure', {}),
                'dependencies': local_analysis.get('dependencies', []),
                'database': local_analysis.get('database', {}),
                'file_stats': local_analysis.get('file_stats', {}),
                'notes': local_analysis.get('notes', ''),
                'business_logic': ''  # Empty business logic for local analysis only
            }
        
        # Store analysis in session
        session['analysis'] = combined_analysis
        session['analysis_timestamp'] = datetime.now().isoformat()
        session.modified = True
        
        current_app.logger.info(f"Analysis completed: {project_id} - {combined_analysis['framework']}")
        
        return jsonify({
            'status': 'success',
            'project_id': project_id,
            'analysis': combined_analysis
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Analysis error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Analysis failed: {str(e)}'
        }), 500

@analysis_bp.route('/confirm-context', methods=['POST'])
@validate_request(ContextValidator)
def confirm_context():
    """
    Confirm or modify project context
    
    Request:
        {
            "purpose": "E-commerce platform",
            "features": ["user auth", "payment gateway"],
            "business_logic": "Process orders and payments"
        }
        
    Response:
        {
            "status": "success",
            "message": "Context confirmed",
            "project_id": "uuid"
        }
    """
    
    try:
        # Get project from session
        project_id = session.get('project_id')
        
        if not project_id:
            return jsonify({
                'status': 'error',
                'message': 'No active project found'
            }), 400
        
        # Get context from request
        context_data = request.get_json()
        
        # Validate required fields
        required_fields = ['purpose', 'features', 'business_logic']
        for field in required_fields:
            if field not in context_data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Store context in session
        session['project_context'] = {
            'purpose': context_data.get('purpose', ''),
            'features': context_data.get('features', []),
            'business_logic': context_data.get('business_logic', ''),
            'requirements': context_data.get('requirements', []),
            'target_framework': context_data.get('target_framework') or context_data.get('target-framework'),  # Support both formats
            'confirmed_at': datetime.now().isoformat()
        }
        session.modified = True
        
        # Log stored context for debugging
        current_app.logger.info(f"Context confirmed via API for project {project_id}: target_framework={session['project_context'].get('target_framework')}")
        
        current_app.logger.info(f"Context confirmed for project: {project_id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Context confirmed successfully',
            'project_id': project_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Context confirmation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Context confirmation failed: {str(e)}'
        }), 500

@analysis_bp.route('/file-analysis/<project_id>', methods=['GET'])
def get_file_analysis(project_id):
    """
    Get file analysis results for a project (for auto-suggestions in context form)
    
    Response:
        {
            "status": "success",
            "analysis": {
                "framework": "Laravel",
                "confidence": 95,
                "structure": {...},
                "dependencies": [...],
                "database": {...},
                "notes": "..."
            },
            "suggestions": {
                "context_type": "web_application",
                "description": "E-commerce platform",
                "features": ["user authentication", "shopping cart"]
            }
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
        
        # Get analysis from session (if available)
        analysis = session.get('analysis')
        
        # If analysis not in session, perform analysis (try AI first, fallback to local)
        if not analysis:
            files_dict = session.get('files_dict')
            
            if not files_dict:
                return jsonify({
                    'status': 'error',
                    'message': 'No project files found. Please upload a project first.'
                }), 400
            
            # Perform local analysis first (fast)
            analyzer = FrameworkAnalyzer()
            local_analysis = analyzer.analyze_structure(files_dict)
            
            # Try AI analysis if API key is available (for better results)
            try:
                api_key = current_app.config.get('GEMINI_API_KEY') or current_app.config.get('ANTHROPIC_API_KEY') or os.getenv('GEMINI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
                if api_key:
                    # Perform AI analysis for better results
                    gemini_service = GeminiService(api_key)
                    ai_analysis = gemini_service.analyze_project_structure(files_dict)
                    
                    # Combine local and AI analysis (prefer AI results)
                    analysis = {
                        'framework': ai_analysis.get('framework', local_analysis.get('primary_framework', 'Unknown')),
                        'confidence': ai_analysis.get('confidence', local_analysis.get('confidence', 0)),
                        'structure': ai_analysis.get('structure', local_analysis.get('structure', {})),
                        'dependencies': ai_analysis.get('dependencies', local_analysis.get('dependencies', [])),
                        'database': ai_analysis.get('database', local_analysis.get('database', {})),
                        'file_stats': local_analysis.get('file_stats', {}),
                        'notes': ai_analysis.get('notes', '') or f"{ai_analysis.get('framework', 'Unknown')} application with {len(ai_analysis.get('dependencies', []))} dependencies",
                        'business_logic': ai_analysis.get('business_logic', '')  # Include business logic from AI analysis
                    }
                else:
                    # No API key, use local analysis only
                    analysis = {
                        'framework': local_analysis.get('primary_framework', 'Unknown'),
                        'confidence': local_analysis.get('confidence', 0),
                        'structure': local_analysis.get('structure', {}),
                        'dependencies': local_analysis.get('dependencies', []),
                        'database': local_analysis.get('database', {}),
                        'file_stats': local_analysis.get('file_stats', {}),
                        'notes': f"{local_analysis.get('primary_framework', 'Unknown')} application detected"
                    }
            except Exception as e:
                current_app.logger.warning(f"AI analysis failed, using local analysis: {str(e)}")
                # Fallback to local analysis
                analysis = {
                    'framework': local_analysis.get('primary_framework', 'Unknown'),
                    'confidence': local_analysis.get('confidence', 0),
                    'structure': local_analysis.get('structure', {}),
                    'dependencies': local_analysis.get('dependencies', []),
                    'database': local_analysis.get('database', {}),
                    'file_stats': local_analysis.get('file_stats', {}),
                    'notes': f"{local_analysis.get('primary_framework', 'Unknown')} application detected",
                    'business_logic': ''  # Empty business logic for local analysis only
                }
            
            # Store in session for future use
            session['analysis'] = analysis
            session.modified = True
        
        # Generate suggestions based on analysis
        suggestions = generate_suggestions_from_analysis(analysis)
        
        return jsonify({
            'status': 'success',
            'analysis': analysis,
            'suggestions': suggestions
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"File analysis error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Analysis failed: {str(e)}'
        }), 500


def generate_suggestions_from_analysis(analysis: dict) -> dict:
    """
    Generate auto-suggestions for context form based on analysis results
    """
    suggestions = {}
    
    # Generate description/purpose from analysis
    framework = analysis.get('framework', 'Unknown')
    notes = analysis.get('notes', '')
    dependencies = analysis.get('dependencies', [])
    business_logic = analysis.get('business_logic', '')  # Get business logic from analysis
    
    # Create purpose description - prioritize notes if available
    if notes:
        # Use notes as description, but truncate if too long
        if len(notes) > 300:
            suggestions['description'] = notes[:300] + "..."
        else:
            suggestions['description'] = notes
    elif framework and framework != 'Unknown':
        purpose_parts = [f"{framework} application"]
        if dependencies:
            purpose_parts.append(f"with {len(dependencies)} dependencies")
        suggestions['description'] = " - ".join(purpose_parts) + " ready for framework conversion"
    else:
        suggestions['description'] = "Code project ready for framework conversion"
    
    # Suggest features based on dependencies
    feature_map = {
        # Authentication & Security
        'auth': 'User Authentication',
        'passport': 'OAuth Authentication',
        'sanctum': 'API Authentication',
        'jwt': 'JWT Authentication',
        'bcrypt': 'Password Security',
        'helmet': 'Security Headers',
        
        # Database
        'mongodb': 'Database Integration',
        'mongoose': 'Database Integration',
        'mysql': 'Database Integration',
        'postgresql': 'Database Integration',
        'sequelize': 'Database Integration',
        'typeorm': 'Database Integration',
        'eloquent': 'ORM',
        'django.db': 'ORM',
        
        # API & Communication
        'express': 'REST API',
        'socket.io': 'Real-time Communication',
        'axios': 'HTTP Client',
        'fetch': 'HTTP Client',
        
        # Payments
        'stripe': 'Payment Processing',
        'paypal': 'Payment Processing',
        
        # Utilities
        'redis': 'Caching',
        'nodemailer': 'Email Notifications',
        'mail': 'Email Notifications',
        'multer': 'File Upload',
        'validator': 'Input Validation',
        'cors': 'Cross-Origin Support',
        'dotenv': 'Configuration Management',
        'morgan': 'Logging',
        'winston': 'Logging',
        'queue': 'Background Jobs',
        'elasticsearch': 'Search Functionality',
        
        # Laravel specific
        'blade': 'Template Engine',
        'artisan': 'CLI Tools',
        
        # Django specific
        'django': 'Admin Panel',
        'flask': 'Microservices',
    }
    
    suggested_features = []
    for dep in dependencies:
        dep_lower = str(dep).lower()
        for key, feature in feature_map.items():
            if key in dep_lower and feature not in suggested_features:
                suggested_features.append(feature)
    
    # Add framework-specific features
    framework_lower = framework.lower()
    if 'laravel' in framework_lower:
        if 'MVC Architecture' not in suggested_features:
            suggested_features.extend(['MVC Architecture', 'Eloquent ORM', 'Blade Templating'])
    elif 'django' in framework_lower:
        if 'MVC Architecture' not in suggested_features:
            suggested_features.extend(['MVC Architecture', 'Admin Panel', 'ORM'])
    elif 'flask' in framework_lower:
        if 'REST API' not in suggested_features:
            suggested_features.extend(['REST API', 'Microservices'])
    elif 'express' in framework_lower:
        if 'REST API' not in suggested_features:
            suggested_features.extend(['REST API', 'Middleware Support', 'Routing'])
    elif 'spring' in framework_lower:
        suggested_features.extend(['Enterprise Architecture', 'Dependency Injection'])
    elif 'asp.net' in framework_lower or 'aspnet' in framework_lower:
        suggested_features.extend(['MVC Architecture', 'Entity Framework'])
    
    # Remove duplicates and limit
    suggested_features = list(dict.fromkeys(suggested_features))  # Preserves order while removing duplicates
    if suggested_features:
        suggestions['features'] = suggested_features[:10]  # Limit to 10 features
    
    # Suggest context type based on framework
    if any(f in framework_lower for f in ['laravel', 'symfony', 'codeigniter', 'django', 'flask', 'express', 'nest', 'spring', 'asp.net']):
        suggestions['context_type'] = 'web_application'
    else:
        suggestions['context_type'] = 'code_project'
    
    # Include business_logic in suggestions if available
    if business_logic and len(business_logic.strip()) > 50:
        suggestions['business_logic'] = business_logic
    elif notes and len(notes.strip()) > 50:
        # Use notes as fallback for business logic
        suggestions['business_logic'] = f"Based on analysis: {notes}. The application implements core functionality through its code structure and business rules."
    else:
        # Generate basic business logic from framework and dependencies
        business_logic_parts = [f"{framework} application"]
        if dependencies:
            business_logic_parts.append(f"using {', '.join(dependencies[:5])} dependencies")
        if suggested_features:
            business_logic_parts.append(f"with features: {', '.join(suggested_features[:5])}")
        suggestions['business_logic'] = ". ".join(business_logic_parts) + ". The application processes user requests, handles data operations, and implements business rules as defined in the code."
    
    return suggestions


@analysis_bp.route('/status/<project_id>', methods=['GET'])
def get_project_status(project_id):
    """
    Get current project status
    
    Response:
        {
            "status": "success",
            "project": {
                "id": "uuid",
                "state": "uploaded|analyzed|converting|completed",
                "progress": 75,
                "current_step": "Converting files"
            }
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
        
        # Get project state from session
        state = 'uploaded'
        progress = 0
        current_step = 'Project uploaded'
        
        if session.get('analysis'):
            state = 'analyzed'
            progress = 33
            current_step = 'Analysis completed'
        
        if session.get('project_context'):
            state = 'context_confirmed'
            progress = 50
            current_step = 'Context confirmed'
        
        if session.get('conversion_progress'):
            state = 'converting'
            progress = session['conversion_progress']
            current_step = session.get('conversion_step', 'Converting files')
        
        if session.get('conversion_complete'):
            state = 'completed'
            progress = 100
            current_step = 'Conversion completed'
        
        return jsonify({
            'status': 'success',
            'project': {
                'id': project_id,
                'state': state,
                'progress': progress,
                'current_step': current_step,
                'upload_timestamp': session.get('upload_timestamp'),
                'analysis': session.get('analysis', {}).get('framework') if session.get('analysis') else None
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Status check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Status check failed: {str(e)}'
        }), 500