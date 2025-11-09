// Context form handling with tags, validation, and framework selection

let features = [];
let requirements = [];

const contextForm = document.getElementById('context-form');
const purposeInput = document.getElementById('purpose');
const featureInput = document.getElementById('feature-input');
const featuresTagsContainer = document.getElementById('features-tags');
const requirementInput = document.getElementById('requirement-input');
const requirementsList = document.getElementById('requirements-list');
const businessLogicInput = document.getElementById('business-logic');
const submitBtn = document.getElementById('submit-btn');
const fileId = document.getElementById('file-id').value;

document.addEventListener('DOMContentLoaded', () => {
    setupForm();
    setupFeatureInput();
    setupRequirementInput();
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

function setupRequirementInput() {
    requirementInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const value = requirementInput.value.trim();
            if (value) {
                addRequirement(value);
                requirementInput.value = '';
            }
        }
    });
}

function addRequirement(reqText) {
    if (requirements.includes(reqText)) {
        showToast('Requirement already added', 'warning');
        return;
    }
    requirements.push(reqText);
    renderRequirements();
}

function removeRequirement(reqText) {
    requirements = requirements.filter(r => r !== reqText);
    renderRequirements();
}

window.removeRequirement = removeRequirement;

function renderRequirements() {
    if (!requirements.length) {
        requirementsList.innerHTML = '<p class="text-gray-400">No requirements added yet</p>';
        return;
    }
    requirementsList.innerHTML = requirements.map((req, i) => `
        <div class="requirement-item">
            <span>${i + 1}. ${escapeHtml(req)}</span>
            <button type="button" class="remove-btn" onclick="removeRequirement('${req.replace(/'/g, "\\'")}')">
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
        if (count > 1000) {
            businessLogicInput.value = businessLogicInput.value.substring(0, 1000);
        }
        validateField('business-logic');
    });
}

function setupFrameworkSelector() {
    const frameworkOptions = document.querySelectorAll('.framework-option');
    frameworkOptions.forEach(option => {
        const radio = option.querySelector('input[type="radio"]');
        const label = option.querySelector('label');
        
        // Make the entire option clickable
        option.addEventListener('click', (e) => {
            if (e.target !== radio && e.target !== label) {
                radio.checked = true;
                updateFrameworkSelection();
            }
        });
        
        radio.addEventListener('change', () => {
            updateFrameworkSelection();
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
    if (Array.isArray(ctx.requirements)) {
        requirements = ctx.requirements.slice();
        renderRequirements();
    }
    
    // Update character counts
    document.getElementById('purpose-count').textContent = purposeInput.value.length;
    document.getElementById('logic-count').textContent = businessLogicInput.value.length;
}

async function loadAutoSuggestions() {
    try {
        const response = await fetch(`/api/file-analysis/${fileId}`);
        if (response.ok) {
            const data = await response.json();
            if (data.analysis) {
                // Auto-fill purpose from analysis notes if available
                if (data.analysis.notes && !purposeInput.value) {
                    // Extract purpose from notes (first sentence)
                    const firstSentence = data.analysis.notes.split('.')[0];
                    if (firstSentence) {
                        purposeInput.value = firstSentence.trim();
                        document.getElementById('purpose-count').textContent = purposeInput.value.length;
                    }
                }
                
                // Auto-suggest features based on dependencies
                if (data.analysis.dependencies && data.analysis.dependencies.length > 0) {
                    // Could suggest features based on dependencies
                }
            }
        }
    } catch (error) {
        console.error('Error loading auto-suggestions:', error);
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
    
    requirements = [
        'Maintain user sessions',
        'Secure payment handling',
        'Email notifications for orders'
    ];
    renderRequirements();
    
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
    
    if (fieldName === 'business-logic' && field.value.length > 1000) {
        isValid = false;
        errorMessage = 'Business logic must be less than 1000 characters';
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
        file_id: fileId,
        purpose: purposeInput.value.trim(),
        features: features,
        business_logic: businessLogicInput.value.trim(),
        requirements: requirements,
        target_framework: targetFrameworkEl.value
    };
    
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
    window.location.href = `/analysis/${fileId}`;
}

window.goBack = goBack;

