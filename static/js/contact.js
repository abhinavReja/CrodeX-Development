// Contact form handling

document.addEventListener('DOMContentLoaded', () => {
    const contactForm = document.getElementById('contact-form');
    
    if (contactForm) {
        contactForm.addEventListener('submit', handleFormSubmit);
        
        // Add real-time validation
        const inputs = contactForm.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', validateField);
            input.addEventListener('input', clearFieldError);
        });
    }
});

function handleFormSubmit(e) {
    const form = e.target;
    const name = form.querySelector('#name').value.trim();
    const email = form.querySelector('#email').value.trim();
    const message = form.querySelector('#message').value.trim();
    
    // Validate required fields
    let isValid = true;
    
    if (!name) {
        showFieldError('name', 'Name is required');
        isValid = false;
    }
    
    if (!email) {
        showFieldError('email', 'Email is required');
        isValid = false;
    } else if (!isValidEmail(email)) {
        showFieldError('email', 'Please enter a valid email address');
        isValid = false;
    }
    
    if (!message) {
        showFieldError('message', 'Message is required');
        isValid = false;
    }
    
    if (!isValid) {
        e.preventDefault();
        showToast('Please fix the errors in the form', 'error');
        return false;
    }
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    }
    
    return true;
}

function validateField(e) {
    const field = e.target;
    const fieldName = field.id;
    const value = field.value.trim();
    
    clearFieldError(fieldName);
    
    if (field.hasAttribute('required') && !value) {
        showFieldError(fieldName, 'This field is required');
        return false;
    }
    
    if (fieldName === 'email' && value && !isValidEmail(value)) {
        showFieldError(fieldName, 'Please enter a valid email address');
        return false;
    }
    
    return true;
}

function clearFieldError(e) {
    const field = e.target;
    const fieldName = field.id;
    const errorElement = document.getElementById(`${fieldName}-error`);
    
    if (errorElement) {
        errorElement.textContent = '';
    }
    
    field.classList.remove('error');
}

function showFieldError(fieldName, message) {
    const field = document.getElementById(fieldName);
    if (!field) return;
    
    // Remove existing error element if any
    const existingError = document.getElementById(`${fieldName}-error`);
    if (existingError) {
        existingError.remove();
    }
    
    // Create error element
    const errorElement = document.createElement('span');
    errorElement.id = `${fieldName}-error`;
    errorElement.className = 'field-error';
    errorElement.textContent = message;
    
    // Insert after the field
    field.parentNode.appendChild(errorElement);
    field.classList.add('error');
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function showToast(message, type = 'success') {
    // Use the existing toast functionality from utils.js if available
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
    } else {
        // Fallback: simple alert
        alert(message);
    }
}

