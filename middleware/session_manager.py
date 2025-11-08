from flask import session
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

def setup_session_manager(app):
    """Setup session management for the application using Flask's built-in session"""
    
    @app.before_request
    def make_session_permanent():
        """Make session permanent with configured lifetime"""
        session.permanent = True
        app.permanent_session_lifetime = app.config.get('PERMANENT_SESSION_LIFETIME', timedelta(hours=24))
    
    logger.info('Session manager configured (using Flask built-in sessions)')

