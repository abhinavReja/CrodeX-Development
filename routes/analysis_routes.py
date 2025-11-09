from flask import Blueprint, request, jsonify, session, current_app
from schemas.context_schema import ContextValidator
from middleware.validation import validate_request
from services.gemini_api import GeminiService
from services.analyzer import FrameworkAnalyzer

analysis_bp = Blueprint('analysis', __name__)

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
        
        # Initialize services
        claude = GeminiService(current_app.config['ANTHROPIC_API_KEY'])
        analyzer = FrameworkAnalyzer()
        
        # Step 1: Quick local analysis
        current_app.logger.info(f"Starting local analysis for {project_id}")
        local_analysis = analyzer.analyze_structure(files_dict)
        
        # Step 2: Claude AI analysis
        current_app.logger.info(f"Starting AI analysis for {project_id}")
        ai_analysis = claude.analyze_project_structure(files_dict)
        
        # Combine results
        combined_analysis = {
            'framework': ai_analysis.get('framework', 'Unknown'),
            'confidence': ai_analysis.get('confidence', 0),
            'structure': ai_analysis.get('structure', {}),
            'dependencies': ai_analysis.get('dependencies', []),
            'database': ai_analysis.get('database', {}),
            'local_detection': local_analysis.get('primary_framework'),
            'file_stats': local_analysis.get('file_stats', {}),
            'notes': ai_analysis.get('notes', '')
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
            "business_logic": "Process orders and payments",
            "requirements": ["maintain user sessions", "secure payments"]
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
            'purpose': context_data['purpose'],
            'features': context_data['features'],
            'business_logic': context_data['business_logic'],
            'requirements': context_data.get('requirements', []),
            'confirmed_at': datetime.now().isoformat()
        }
        session.modified = True
        
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