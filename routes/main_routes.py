from flask import Blueprint, render_template, jsonify, request, flash, current_app

main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET'])
def index():
    """Home page"""
    return render_template('index.html')

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            subject = request.form.get('subject', '').strip()
            message = request.form.get('message', '').strip()
            
            # Validate required fields
            if not name or not email or not message:
                flash('Please fill in all required fields.', 'error')
                return render_template('contact.html')
            
            # Basic email validation
            if '@' not in email or '.' not in email:
                flash('Please enter a valid email address.', 'error')
                return render_template('contact.html')
            
            # Log the contact form submission (since we don't have email configured)
            current_app.logger.info(f"Contact form submission - Name: {name}, Email: {email}, Subject: {subject}, Message: {message[:100]}...")
            
            # In a production environment, you would send an email here
            # For now, we'll just show a success message
            flash('Thank you for contacting us! We will get back to you soon.', 'success')
            return render_template('contact.html', submitted=True)
            
        except Exception as e:
            current_app.logger.error(f"Error processing contact form: {str(e)}")
            flash('An error occurred while sending your message. Please try again later.', 'error')
            return render_template('contact.html')
    
    return render_template('contact.html')

@main_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'converter-api',
        'version': '1.0.0'
    }), 200
