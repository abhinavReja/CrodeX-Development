// Context form handling with tags, validation, and framework selection

let features = [];

const contextForm = document.getElementById('context-form');
const purposeInput = document.getElementById('purpose');
const featureInput = document.getElementById('feature-input');
const featuresTagsContainer = document.getElementById('features-tags');
const businessLogicInput = document.getElementById('business-logic');
const submitBtn = document.getElementById('submit-btn');

// Get project_id and file_id - will be set after DOM loads
let fileId = null;
let projectId = null;

document.addEventListener('DOMContentLoaded', () => {
    // Get project_id and file_id from hidden inputs
    const fileIdInput = document.getElementById('file-id');
    const projectIdInput = document.getElementById('project-id');
    fileId = fileIdInput ? fileIdInput.value : null;
    projectId = projectIdInput ? projectIdInput.value : fileId;  // Use project_id if available, fallback to file_id
    
    setupForm();
    setupFeatureInput();
    setupCharacterCounters();
    setupFrameworkSelector();
    loadPreviousContext();
    loadAutoSuggestions();
});

function setupForm() {
    contextForm.addEventListener('submit', handleSubmit);
}

function setupFeatureInput() {
    featureInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const value = featureInput.value.trim();
            if (value) {
                addFeature(value);
                featureInput.value = '';
            }
        }
    });
}

function addFeature(featureText) {
    if (features.includes(featureText)) {
        showToast('Feature already added', 'warning');
        return;
    }
    features.push(featureText);
    renderFeatures();
    clearFieldError('features');
}

window.addFeature = addFeature; // used by "Use This Example" buttons

function removeFeature(featureText) {
    features = features.filter(f => f !== featureText);
    renderFeatures();
}

window.removeFeature = removeFeature;

function renderFeatures() {
    if (!features.length) {
        featuresTagsContainer.innerHTML = '<p class="text-gray-400">No features added yet</p>';
        return;
    }
    featuresTagsContainer.innerHTML = features.map(f => `
        <div class="feature-tag">
            <span>${escapeHtml(f)}</span>
            <button type="button" class="remove-tag" onclick="removeFeature('${f.replace(/'/g, "\\'")}')">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `).join('');
}

function setupCharacterCounters() {
    purposeInput.addEventListener('input', () => {
        const count = purposeInput.value.length;
        document.getElementById('purpose-count').textContent = count;
        if (count > 500) {
            purposeInput.value = purposeInput.value.substring(0, 500);
        }
        validateField('purpose');
    });
    
    businessLogicInput.addEventListener('input', () => {
        const count = businessLogicInput.value.length;
        document.getElementById('logic-count').textContent = count;
        // Increase limit to 5000 characters for detailed business logic
        if (count > 5000) {
            businessLogicInput.value = businessLogicInput.value.substring(0, 5000);
            document.getElementById('logic-count').textContent = 5000;
        }
        validateField('business-logic');
    });
}

function setupFrameworkSelector() {
    const frameworkOptions = document.querySelectorAll('.framework-option');
    frameworkOptions.forEach(option => {
        const radio = option.querySelector('input[type="radio"]');
        const label = option.querySelector('label');
        
        // Skip if this is a coming-soon framework
        if (option.classList.contains('coming-soon') || radio.disabled) {
            option.style.cursor = 'not-allowed';
            return;
        }
        
        // Make the entire option clickable
        option.addEventListener('click', (e) => {
            if (e.target !== radio && e.target !== label && !radio.disabled) {
                radio.checked = true;
                updateFrameworkSelection();
            }
        });
        
        radio.addEventListener('change', () => {
            if (!radio.disabled) {
                updateFrameworkSelection();
            }
        });
    });
}

function updateFrameworkSelection() {
    const frameworkOptions = document.querySelectorAll('.framework-option');
    frameworkOptions.forEach(option => {
        const radio = option.querySelector('input[type="radio"]');
        if (radio.checked) {
            option.classList.add('selected');
        } else {
            option.classList.remove('selected');
        }
    });
    clearFieldError('target-framework');
}

function loadPreviousContext() {
    const ctx = State.getContext();
    if (!ctx) return;
    
    if (ctx.purpose) purposeInput.value = ctx.purpose;
    if (ctx.business_logic || ctx.businessLogic) businessLogicInput.value = ctx.business_logic || ctx.businessLogic;
    if (Array.isArray(ctx.features)) {
        features = ctx.features.slice();
        renderFeatures();
    }
    
    // Update character counts
    document.getElementById('purpose-count').textContent = purposeInput.value.length;
    document.getElementById('logic-count').textContent = businessLogicInput.value.length;
}

async function loadAutoSuggestions() {
    try {
        // Use project_id if available, otherwise file_id
        const id = projectId || fileId;
        if (!id) {
            console.warn('No project ID or file ID available for auto-suggestions');
            return;
        }
        
        // Show loading indicator
        const purposeField = document.getElementById('purpose');
        if (purposeField && !purposeField.value) {
            purposeField.placeholder = 'Analyzing project...';
        }
        
        const response = await fetch(`/api/file-analysis/${id}`);
        if (response.ok) {
            const data = await response.json();
            if (data.status === 'success' && data.analysis) {
                // Auto-fill purpose from analysis
                if (!purposeInput.value) {
                    if (data.analysis.notes) {
                        // Use notes as purpose
                        purposeInput.value = data.analysis.notes.trim();
                        document.getElementById('purpose-count').textContent = purposeInput.value.length;
                    } else if (data.analysis.framework) {
                        // Create purpose from framework detection
                        purposeInput.value = `${data.analysis.framework} application - ${data.analysis.framework} project ready for conversion`;
                        document.getElementById('purpose-count').textContent = purposeInput.value.length;
                    }
                }
                
                // Auto-suggest features based on dependencies
                if (data.analysis.dependencies && data.analysis.dependencies.length > 0 && features.length === 0) {
                    // Suggest features based on common dependencies
                    const dependencyFeatures = {
                        'express': 'REST API',
                        'mongodb': 'Database Integration',
                        'mysql': 'Database Integration',
                        'redis': 'Caching',
                        'jwt': 'User Authentication',
                        'passport': 'User Authentication',
                        'bcrypt': 'Password Security',
                        'nodemailer': 'Email Notifications',
                        'socket.io': 'Real-time Communication',
                        'multer': 'File Upload',
                        'validator': 'Input Validation',
                        'cors': 'Cross-Origin Support'
                    };
                    
                    data.analysis.dependencies.forEach(dep => {
                        const depLower = dep.toLowerCase();
                        for (const [key, feature] of Object.entries(dependencyFeatures)) {
                            if (depLower.includes(key) && !features.includes(feature)) {
                                features.push(feature);
                            }
                        }
                    });
                    
                    if (features.length > 0) {
                        renderFeatures();
                    }
                }
                
                // Apply suggestions if available
                if (data.suggestions) {
                    if (data.suggestions.description && !purposeInput.value) {
                        purposeInput.value = data.suggestions.description;
                        document.getElementById('purpose-count').textContent = purposeInput.value.length;
                    }
                    
                    if (data.suggestions.features && Array.isArray(data.suggestions.features) && features.length === 0) {
                        features = data.suggestions.features.slice();
                        renderFeatures();
                    }
                    
                    // Auto-fill business_logic from suggestions (priority) or from analysis
                    if (!businessLogicInput.value || businessLogicInput.value.trim().length < 50) {
                        if (data.suggestions.business_logic && data.suggestions.business_logic.trim().length > 50) {
                            businessLogicInput.value = data.suggestions.business_logic.trim();
                            document.getElementById('logic-count').textContent = businessLogicInput.value.length;
                        } else if (data.analysis.business_logic && data.analysis.business_logic.trim().length > 50) {
                            businessLogicInput.value = data.analysis.business_logic.trim();
                            document.getElementById('logic-count').textContent = businessLogicInput.value.length;
                        } else if (data.analysis.notes && data.analysis.notes.trim().length > 50) {
                            // Use notes as fallback for business logic
                            businessLogicInput.value = `Based on analysis: ${data.analysis.notes}. The application implements core functionality through its code structure and business rules.`;
                            document.getElementById('logic-count').textContent = businessLogicInput.value.length;
                        }
                    }
                } else if (data.analysis) {
                    // If no suggestions, try to use analysis data directly
                    if (!businessLogicInput.value || businessLogicInput.value.trim().length < 50) {
                        if (data.analysis.business_logic && data.analysis.business_logic.trim().length > 50) {
                            businessLogicInput.value = data.analysis.business_logic.trim();
                            document.getElementById('logic-count').textContent = businessLogicInput.value.length;
                        } else if (data.analysis.notes && data.analysis.notes.trim().length > 50) {
                            businessLogicInput.value = `Based on analysis: ${data.analysis.notes}. The application implements core functionality through its code structure and business rules.`;
                            document.getElementById('logic-count').textContent = businessLogicInput.value.length;
                        }
                    }
                }
                
                // Auto-select framework if detected
                if (data.analysis.framework) {
                    const frameworkMap = {
                        'Laravel': 'laravel',
                        'Django': 'django',
                        'Flask': 'flask',
                        'Express.js': 'express',
                        'Express': 'express',
                        'Spring Boot': 'spring',
                        'ASP.NET Core': 'aspnet'
                    };
                    
                    const frameworkKey = frameworkMap[data.analysis.framework];
                    if (frameworkKey) {
                        const frameworkRadio = document.getElementById(frameworkKey);
                        if (frameworkRadio && !document.querySelector('input[name="target-framework"]:checked')) {
                            frameworkRadio.checked = true;
                            updateFrameworkSelection();
                        }
                    }
                }
                
                // Show success message
                if (purposeInput.value || features.length > 0) {
                    showToast('Analysis complete! Form auto-filled with suggestions.', 'success');
                }
            }
        } else {
            console.error('Error loading auto-suggestions:', response.status, response.statusText);
        }
    } catch (error) {
        console.error('Error loading auto-suggestions:', error);
    } finally {
        // Reset placeholder
        const purposeField = document.getElementById('purpose');
        if (purposeField && purposeField.placeholder === 'Analyzing project...') {
            purposeField.placeholder = 'Describe what your application does (e.g., E-commerce platform for selling products)';
        }
    }
}

function fillExampleContext() {
    purposeInput.value = 'Online marketplace for buying and selling electronics';
    document.getElementById('purpose-count').textContent = purposeInput.value.length;
    
    features = [
        'User Authentication',
        'Product Catalog',
        'Shopping Cart',
        'Payment Processing',
        'Order Tracking'
    ];
    renderFeatures();
    
    businessLogicInput.value = 'Users can register, browse products by category, add items to cart, checkout with multiple payment options, and track their orders. Admin can manage products and view sales analytics.';
    document.getElementById('logic-count').textContent = businessLogicInput.value.length;
    
    // Select Django as default framework
    const djangoRadio = document.getElementById('django');
    if (djangoRadio) {
        djangoRadio.checked = true;
        updateFrameworkSelection();
    }
    
    showToast('Example context loaded', 'success');
}

window.fillExampleContext = fillExampleContext;

function validateField(fieldName) {
    const field = document.getElementById(fieldName);
    if (!field) return true;
    
    const errorSpan = document.getElementById(`${fieldName}-error`);
    let isValid = true;
    let errorMessage = '';
    
    if (field.hasAttribute('required') && !field.value.trim()) {
        isValid = false;
        errorMessage = 'This field is required';
    }
    
    if (fieldName === 'purpose' && field.value.length > 500) {
        isValid = false;
        errorMessage = 'Purpose must be less than 500 characters';
    }
    
    if (fieldName === 'business-logic' && field.value.length > 5000) {
        isValid = false;
        errorMessage = 'Business logic must be less than 5000 characters';
    }
    
    if (errorSpan) {
        if (isValid) {
            errorSpan.textContent = '';
            field.classList.remove('error');
        } else {
            errorSpan.textContent = errorMessage;
            field.classList.add('error');
        }
    }
    
    return isValid;
}

function clearFieldError(fieldName) {
    const errorSpan = document.getElementById(`${fieldName}-error`);
    const field = document.getElementById(fieldName);
    if (errorSpan) errorSpan.textContent = '';
    if (field) field.classList.remove('error');
}

function validateForm() {
    let isValid = true;
    
    // Validate purpose
    if (!validateField('purpose')) {
        isValid = false;
    }
    
    // Validate features
    if (features.length === 0) {
        showFieldError('features', 'Please add at least one feature');
        isValid = false;
    } else {
        clearFieldError('features');
    }
    
    // Validate business logic
    if (!validateField('business-logic')) {
        isValid = false;
    }
    
    // Validate target framework
    const targetFramework = document.querySelector('input[name="target-framework"]:checked');
    if (!targetFramework) {
        showFieldError('target-framework', 'Please select a target framework');
        isValid = false;
    } else {
        clearFieldError('target-framework');
    }
    
    return isValid;
}

function showFieldError(fieldName, message) {
    const errorSpan = document.getElementById(`${fieldName}-error`);
    if (errorSpan) {
        errorSpan.textContent = message;
    }
    const field = document.getElementById(fieldName);
    if (field) {
        field.classList.add('error');
    }
}

async function handleSubmit(e) {
    e.preventDefault();
    
    if (!validateForm()) {
        showToast('Please fix the errors in the form', 'error');
        return;
    }
    
    const targetFrameworkEl = document.querySelector('input[name="target-framework"]:checked');
    if (!targetFrameworkEl) {
        showToast('Please select a target framework', 'warning');
        return;
    }
    
    const contextData = {
        purpose: purposeInput.value.trim(),
        features: features,
        business_logic: businessLogicInput.value.trim(),
        target_framework: targetFrameworkEl.value
    };
    
    // Include project_id if available (preferred), otherwise file_id for backward compatibility
    if (projectId) {
        contextData.project_id = projectId;
    } else if (fileId) {
        contextData.file_id = fileId;
    }
    
    // Store in state
    State.setContext(contextData);
    State.setTargetFramework(targetFrameworkEl.value);
    
    showLoading('Confirming context...');
    submitBtn.disabled = true;
    
    try {
        const response = await fetch(contextForm.action, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(contextData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            hideLoading();
            showToast('Context confirmed!', 'success');
            
            // Redirect to progress page
            if (result.redirect_url) {
                setTimeout(() => {
                    window.location.href = result.redirect_url;
                }, 600);
            } else if (result.task_id) {
                setTimeout(() => {
                    window.location.href = `/progress/${result.task_id}`;
                }, 600);
            } else {
                setTimeout(() => {
                    window.location.href = '/';
                }, 600);
            }
        } else {
            throw new Error(result.message || 'Failed to confirm context');
        }
    } catch (err) {
        console.error(err);
        hideLoading();
        submitBtn.disabled = false;
        showToast('Failed to confirm context: ' + err.message, 'error');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function goBack() {
    // Go back to upload page
    window.location.href = '/upload';
}

window.goBack = goBack;

