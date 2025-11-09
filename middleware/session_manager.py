from flask import session
from datetime import datetime, timedelta

def setup_session_manager(app):
    """Setup session management hooks"""
    
    @app.before_request
    def check_session_timeout():
        """Check if session has timed out"""
        if 'upload_timestamp' in session:
            upload_time = datetime.fromisoformat(session['upload_timestamp'])
            max_age = timedelta(hours=app.config['MAX_PROJECT_AGE_HOURS'])
            
            if datetime.now() - upload_time > max_age:
                # Session expired, cleanup
                session.clear()
    
    @app.after_request
    def update_session_activity(response):
        """Update last activity timestamp"""
        if 'project_id' in session:
            session['last_activity'] = datetime.now().isoformat()
            session.modified = True
        
        return response

def get_session_data():
    """Get all session data"""
    return {
        'project_id': session.get('project_id'),
        'upload_timestamp': session.get('upload_timestamp'),
        'analysis': session.get('analysis'),
        'context': session.get('project_context'),
        'conversion_complete': session.get('conversion_complete', False),
        'last_activity': session.get('last_activity')
    }

def clear_session_data():
    """Clear all session data"""
    session.clear()


### *10. Validation Schemas* (schemas/upload_schema.py)
