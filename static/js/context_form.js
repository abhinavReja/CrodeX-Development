// Enhanced Context Form with Dynamic Fields, Auto-suggestions, Validation, and Feature Checkboxes

document.addEventListener('DOMContentLoaded', function() {
    const contextTypeSelect = document.getElementById('context-type');
    const dynamicFieldsContainer = document.getElementById('dynamic-fields');
    const contextForm = document.getElementById('context-form');
    const fileId = document.getElementById('file-id').value;
    const descriptionField = document.getElementById('description');
    const validationMessages = document.getElementById('validation-messages');
    const suggestionsBanner = document.getElementById('suggestions-banner');
    const suggestionsContent = document.getElementById('suggestions-content');
    const featureCheckboxesGroup = document.getElementById('feature-checkboxes-group');
    const featureCheckboxes = document.getElementById('feature-checkboxes');
    const submitBtn = document.getElementById('submit-btn');

    // Auto-suggestions data (would typically come from API)
    let autoSuggestions = {};
    let currentSuggestions = [];

    // Feature definitions
    const availableFeatures = {
        document: [
            { id: 'extract_text', name: 'Extract Text', description: 'Extract text content from documents' },
            { id: 'ocr', name: 'OCR', description: 'Optical Character Recognition' },
            { id: 'convert_format', name: 'Convert Format', description: 'Convert to different formats' },
            { id: 'compress', name: 'Compress', description: 'Reduce file size' },
            { id: 'watermark', name: 'Add Watermark', description: 'Add watermark to documents' }
        ],
        image: [
            { id: 'resize', name: 'Resize', description: 'Resize images' },
            { id: 'convert_format', name: 'Convert Format', description: 'Convert image format' },
            { id: 'ocr', name: 'OCR', description: 'Extract text from images' },
            { id: 'compress', name: 'Compress', description: 'Compress image files' },
            { id: 'enhance', name: 'Enhance', description: 'Enhance image quality' },
            { id: 'remove_bg', name: 'Remove Background', description: 'Remove image background' }
        ],
        code: [
            { id: 'format', name: 'Format Code', description: 'Format and beautify code' },
            { id: 'minify', name: 'Minify', description: 'Minify code files' },
            { id: 'analyze', name: 'Analyze', description: 'Code analysis and linting' },
            { id: 'convert', name: 'Convert Syntax', description: 'Convert between languages' },
            { id: 'document', name: 'Generate Documentation', description: 'Generate code documentation' }
        ],
        data: [
            { id: 'convert_format', name: 'Convert Format', description: 'Convert between data formats' },
            { id: 'validate', name: 'Validate', description: 'Validate data structure' },
            { id: 'clean', name: 'Clean Data', description: 'Clean and sanitize data' },
            { id: 'transform', name: 'Transform', description: 'Transform data structure' },
            { id: 'analyze', name: 'Analyze', description: 'Data analysis and statistics' }
        ],
        archive: [
            { id: 'extract', name: 'Extract', description: 'Extract archive contents' },
            { id: 'compress', name: 'Compress', description: 'Compress files into archive' },
            { id: 'convert_format', name: 'Convert Format', description: 'Convert archive format' },
            { id: 'password_protect', name: 'Password Protect', description: 'Add password protection' },
            { id: 'split', name: 'Split Archive', description: 'Split large archives' }
        ],
        other: [
            { id: 'convert_format', name: 'Convert Format', description: 'Convert file format' },
            { id: 'compress', name: 'Compress', description: 'Compress file' },
            { id: 'analyze', name: 'Analyze', description: 'File analysis' }
        ]
    };

    // Initialize form
    initializeForm();

    // Initialize form
    function initializeForm() {
        // Load auto-suggestions from API
        loadAutoSuggestions();

        // Set up autocomplete for description field
        setupAutocomplete();

        // Context type change handler
        contextTypeSelect.addEventListener('change', function() {
            const contextType = this.value;
            clearValidationErrors();
            updateDynamicFields(contextType);
            updateFeatureCheckboxes(contextType);
        });

        // Real-time validation
        setupRealTimeValidation();

        // Form submission handler
        contextForm.addEventListener('submit', handleFormSubmit);
    }

    // Load auto-suggestions from API
    async function loadAutoSuggestions() {
        try {
            const response = await fetch(`/api/file-analysis/${fileId}`);
            if (response.ok) {
                const data = await response.json();
                autoSuggestions = data.suggestions || {};
                displayAutoSuggestions(autoSuggestions);
            }
        } catch (error) {
            console.error('Error loading auto-suggestions:', error);
        }
    }

    // Display auto-suggestions
    function displayAutoSuggestions(suggestions) {
        if (!suggestions || Object.keys(suggestions).length === 0) {
            return;
        }

        const suggestionItems = [];

        if (suggestions.context_type) {
            suggestionItems.push(`<div class="suggestion-item" data-field="context-type" data-value="${suggestions.context_type}">
                <strong>Context Type:</strong> ${suggestions.context_type}
                <button type="button" class="btn-apply-suggestion" data-field="context-type" data-value="${suggestions.context_type}">Apply</button>
            </div>`);
        }

        if (suggestions.description) {
            suggestionItems.push(`<div class="suggestion-item" data-field="description" data-value="${suggestions.description}">
                <strong>Description:</strong> ${suggestions.description}
                <button type="button" class="btn-apply-suggestion" data-field="description" data-value="${suggestions.description}">Apply</button>
            </div>`);
        }

        if (suggestions.features && suggestions.features.length > 0) {
            suggestionItems.push(`<div class="suggestion-item">
                <strong>Suggested Features:</strong> ${suggestions.features.join(', ')}
                <button type="button" class="btn-apply-suggestion" data-field="features" data-value='${JSON.stringify(suggestions.features)}'>Apply All</button>
            </div>`);
        }

        if (suggestionItems.length > 0) {
            suggestionsContent.innerHTML = suggestionItems.join('');
            suggestionsBanner.style.display = 'block';

            // Add event listeners to apply buttons
            document.querySelectorAll('.btn-apply-suggestion').forEach(btn => {
                btn.addEventListener('click', function() {
                    const field = this.dataset.field;
                    const value = this.dataset.value;
                    applySuggestion(field, value);
                });
            });
        }
    }

    // Apply suggestion
    function applySuggestion(field, value) {
        if (field === 'context-type') {
            contextTypeSelect.value = value;
            contextTypeSelect.dispatchEvent(new Event('change'));
        } else if (field === 'description') {
            descriptionField.value = value;
            descriptionField.dispatchEvent(new Event('input'));
        } else if (field === 'features') {
            const features = JSON.parse(value);
            features.forEach(featureId => {
                const checkbox = document.getElementById(`feature-${featureId}`);
                if (checkbox) {
                    checkbox.checked = true;
                }
            });
        }
    }

    // Close suggestions banner
    document.getElementById('close-suggestions')?.addEventListener('click', function() {
        suggestionsBanner.style.display = 'none';
    });

    // Setup autocomplete for description field
    function setupAutocomplete() {
        const autocompleteContainer = document.getElementById('description-suggestions');
        let autocompleteTimeout;

        descriptionField.addEventListener('input', function() {
            clearTimeout(autocompleteTimeout);
            const value = this.value.trim();

            if (value.length < 2) {
                autocompleteContainer.innerHTML = '';
                autocompleteContainer.classList.remove('show');
                return;
            }

            autocompleteTimeout = setTimeout(() => {
                fetchAutocompleteSuggestions(value);
            }, 300);
        });

        // Hide autocomplete on blur
        descriptionField.addEventListener('blur', function() {
            setTimeout(() => {
                autocompleteContainer.classList.remove('show');
            }, 200);
        });
    }

    // Fetch autocomplete suggestions
    async function fetchAutocompleteSuggestions(query) {
        try {
            const response = await fetch(`/api/autocomplete/description?q=${encodeURIComponent(query)}&file_id=${fileId}`);
            if (response.ok) {
                const data = await response.json();
                displayAutocompleteSuggestions(data.suggestions || []);
            }
        } catch (error) {
            console.error('Error fetching autocomplete:', error);
        }
    }

    // Display autocomplete suggestions
    function displayAutocompleteSuggestions(suggestions) {
        const autocompleteContainer = document.getElementById('description-suggestions');
        
        if (suggestions.length === 0) {
            autocompleteContainer.innerHTML = '';
            autocompleteContainer.classList.remove('show');
            return;
        }

        const suggestionsHTML = suggestions.map(suggestion => {
            return `<div class="autocomplete-item" data-value="${suggestion}">${suggestion}</div>`;
        }).join('');

        autocompleteContainer.innerHTML = suggestionsHTML;
        autocompleteContainer.classList.add('show');

        // Add click handlers
        autocompleteContainer.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', function() {
                descriptionField.value = this.dataset.value;
                autocompleteContainer.classList.remove('show');
                descriptionField.focus();
            });
        });
    }

    // Update dynamic fields based on context type
    function updateDynamicFields(contextType) {
        dynamicFieldsContainer.innerHTML = '';

        if (!contextType) {
            return;
        }

        const fieldConfigs = getFieldConfigs(contextType);
        fieldConfigs.forEach(config => {
            const fieldGroup = createFieldElement(config);
            dynamicFieldsContainer.appendChild(fieldGroup);
        });
    }

    // Get field configurations
    function getFieldConfigs(contextType) {
        const configs = {
            document: [
                { name: 'document_type', label: 'Document Type', type: 'select', options: ['PDF', 'Word', 'Text', 'Markdown', 'HTML', 'Other'], required: true },
                { name: 'language', label: 'Language', type: 'autocomplete', placeholder: 'e.g., English, Spanish', suggestions: ['English', 'Spanish', 'French', 'German', 'Italian'] },
                { name: 'page_count', label: 'Number of Pages', type: 'number', placeholder: 'Enter page count' },
                { name: 'purpose', label: 'Purpose', type: 'textarea', placeholder: 'What is this document for?', required: false }
            ],
            image: [
                { name: 'image_type', label: 'Image Type', type: 'select', options: ['Photo', 'Screenshot', 'Diagram', 'Chart', 'Logo', 'Other'], required: true },
                { name: 'contains_text', label: 'Contains Text', type: 'checkbox', labelText: 'Yes, this image contains text' },
                { name: 'image_format', label: 'Current Format', type: 'select', options: ['JPEG', 'PNG', 'GIF', 'BMP', 'SVG', 'Other'] },
                { name: 'extraction_purpose', label: 'Extraction Purpose', type: 'textarea', placeholder: 'What do you want to extract from this image?' }
            ],
            code: [
                { name: 'programming_language', label: 'Programming Language', type: 'autocomplete', placeholder: 'e.g., Python, JavaScript, Java', suggestions: ['Python', 'JavaScript', 'Java', 'C++', 'C#', 'Go', 'Rust', 'TypeScript'], required: true },
                { name: 'framework', label: 'Framework', type: 'autocomplete', placeholder: 'e.g., Flask, React, Spring', suggestions: ['Flask', 'React', 'Spring', 'Django', 'Vue', 'Angular'] },
                { name: 'purpose', label: 'Code Purpose', type: 'textarea', placeholder: 'What does this code do?' }
            ],
            data: [
                { name: 'data_type', label: 'Data Type', type: 'select', options: ['CSV', 'JSON', 'Excel', 'XML', 'Database', 'Other'], required: true },
                { name: 'has_headers', label: 'Has Headers', type: 'checkbox', labelText: 'Yes, the data has headers' },
                { name: 'row_count', label: 'Approximate Row Count', type: 'number', placeholder: 'Enter row count' },
                { name: 'data_purpose', label: 'Data Purpose', type: 'textarea', placeholder: 'What do you want to do with this data?' }
            ],
            archive: [
                { name: 'archive_type', label: 'Archive Type', type: 'select', options: ['ZIP', 'RAR', '7Z', 'TAR', 'GZ', 'Other'], required: true },
                { name: 'contains_code', label: 'Contains Code', type: 'checkbox', labelText: 'Yes, archive contains code files' },
                { name: 'contains_images', label: 'Contains Images', type: 'checkbox', labelText: 'Yes, archive contains images' },
                { name: 'extraction_purpose', label: 'Extraction Purpose', type: 'textarea', placeholder: 'What do you want to do with this archive?' }
            ],
            other: [
                { name: 'file_category', label: 'File Category', type: 'text', placeholder: 'Describe the category', required: true },
                { name: 'special_requirements', label: 'Special Requirements', type: 'textarea', placeholder: 'Any special processing requirements?' }
            ]
        };

        return configs[contextType] || [];
    }

    // Create field element
    function createFieldElement(config) {
        const div = document.createElement('div');
        div.className = 'form-group';

        const label = document.createElement('label');
        label.setAttribute('for', config.name);
        label.innerHTML = config.label + (config.required ? ' <span class="required">*</span>' : '');
        div.appendChild(label);

        let inputElement;

        if (config.type === 'select') {
            inputElement = createSelectField(config);
        } else if (config.type === 'checkbox') {
            inputElement = createCheckboxField(config);
        } else if (config.type === 'textarea') {
            inputElement = createTextareaField(config);
        } else if (config.type === 'autocomplete') {
            inputElement = createAutocompleteField(config);
        } else if (config.type === 'number') {
            inputElement = createNumberField(config);
        } else {
            inputElement = createTextField(config);
        }

        div.appendChild(inputElement);

        // Add error span
        const errorSpan = document.createElement('span');
        errorSpan.className = 'field-error';
        errorSpan.id = `${config.name}-error`;
        div.appendChild(errorSpan);

        return div;
    }

    // Create select field
    function createSelectField(config) {
        const select = document.createElement('select');
        select.id = config.name;
        select.name = config.name;
        select.className = 'form-control';
        if (config.required) select.required = true;

        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = `Select ${config.label}`;
        select.appendChild(defaultOption);

        config.options.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option.toLowerCase();
            optionElement.textContent = option;
            select.appendChild(optionElement);
        });

        return select;
    }

    // Create checkbox field
    function createCheckboxField(config) {
        const checkboxDiv = document.createElement('div');
        checkboxDiv.className = 'checkbox-group';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = config.name;
        checkbox.name = config.name;
        checkbox.value = 'true';

        const checkboxLabel = document.createElement('label');
        checkboxLabel.setAttribute('for', config.name);
        checkboxLabel.className = 'checkbox-label';
        checkboxLabel.textContent = config.labelText;

        checkboxDiv.appendChild(checkbox);
        checkboxDiv.appendChild(checkboxLabel);
        return checkboxDiv;
    }

    // Create textarea field
    function createTextareaField(config) {
        const textarea = document.createElement('textarea');
        textarea.id = config.name;
        textarea.name = config.name;
        textarea.className = 'form-control';
        textarea.rows = config.rows || 3;
        textarea.placeholder = config.placeholder || '';
        if (config.required) textarea.required = true;

        return textarea;
    }

    // Create autocomplete field
    function createAutocompleteField(config) {
        const wrapper = document.createElement('div');
        wrapper.className = 'autocomplete-wrapper';

        const input = document.createElement('input');
        input.type = 'text';
        input.id = config.name;
        input.name = config.name;
        input.className = 'form-control autocomplete-input';
        input.placeholder = config.placeholder || '';
        if (config.required) input.required = true;
        input.setAttribute('data-suggestions', JSON.stringify(config.suggestions || []));

        const suggestionsDiv = document.createElement('div');
        suggestionsDiv.className = 'autocomplete-suggestions';
        suggestionsDiv.id = `${config.name}-suggestions`;

        wrapper.appendChild(input);
        wrapper.appendChild(suggestionsDiv);

        // Setup autocomplete for this field
        setupFieldAutocomplete(input, suggestionsDiv, config.suggestions || []);

        return wrapper;
    }

    // Setup field autocomplete
    function setupFieldAutocomplete(input, suggestionsContainer, suggestions) {
        input.addEventListener('input', function() {
            const value = this.value.toLowerCase().trim();
            if (value.length === 0) {
                suggestionsContainer.classList.remove('show');
                return;
            }

            const filtered = suggestions.filter(s => s.toLowerCase().includes(value));
            if (filtered.length > 0) {
                suggestionsContainer.innerHTML = filtered.map(s => {
                    return `<div class="autocomplete-item" data-value="${s}">${s}</div>`;
                }).join('');

                suggestionsContainer.classList.add('show');

                suggestionsContainer.querySelectorAll('.autocomplete-item').forEach(item => {
                    item.addEventListener('click', function() {
                        input.value = this.dataset.value;
                        suggestionsContainer.classList.remove('show');
                    });
                });
            } else {
                suggestionsContainer.classList.remove('show');
            }
        });

        input.addEventListener('blur', function() {
            setTimeout(() => {
                suggestionsContainer.classList.remove('show');
            }, 200);
        });
    }

    // Create number field
    function createNumberField(config) {
        const input = document.createElement('input');
        input.type = 'number';
        input.id = config.name;
        input.name = config.name;
        input.className = 'form-control';
        input.placeholder = config.placeholder || '';
        input.min = config.min || 0;
        if (config.required) input.required = true;

        return input;
    }

    // Create text field
    function createTextField(config) {
        const input = document.createElement('input');
        input.type = 'text';
        input.id = config.name;
        input.name = config.name;
        input.className = 'form-control';
        input.placeholder = config.placeholder || '';
        if (config.required) input.required = true;

        return input;
    }

    // Update feature checkboxes
    function updateFeatureCheckboxes(contextType) {
        featureCheckboxes.innerHTML = '';

        if (!contextType || !availableFeatures[contextType]) {
            featureCheckboxesGroup.style.display = 'none';
            return;
        }

        featureCheckboxesGroup.style.display = 'block';
        const features = availableFeatures[contextType];

        features.forEach(feature => {
            const checkboxDiv = document.createElement('div');
            checkboxDiv.className = 'feature-checkbox-item';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `feature-${feature.id}`;
            checkbox.name = 'features';
            checkbox.value = feature.id;
            checkbox.className = 'feature-checkbox';

            const label = document.createElement('label');
            label.setAttribute('for', `feature-${feature.id}`);
            label.className = 'feature-label';
            label.innerHTML = `<strong>${feature.name}</strong><span class="feature-desc">${feature.description}</span>`;

            // Add change handler for styling
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    checkboxDiv.classList.add('checked');
                } else {
                    checkboxDiv.classList.remove('checked');
                }
            });

            checkboxDiv.appendChild(checkbox);
            checkboxDiv.appendChild(label);
            featureCheckboxes.appendChild(checkboxDiv);
        });
    }

    // Setup real-time validation
    function setupRealTimeValidation() {
        contextForm.addEventListener('input', function(e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') {
                validateField(e.target);
            }
        });

        contextForm.addEventListener('change', function(e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') {
                validateField(e.target);
            }
        });
    }

    // Validate field
    function validateField(field) {
        const errorSpan = document.getElementById(`${field.name || field.id}-error`);
        if (!errorSpan) return;

        const errors = [];

        // Required validation
        if (field.required && !field.value.trim()) {
            errors.push('This field is required');
        }

        // Custom validations
        if (field.type === 'email' && field.value && !isValidEmail(field.value)) {
            errors.push('Please enter a valid email address');
        }

        if (field.type === 'number' && field.value) {
            const num = parseInt(field.value);
            if (isNaN(num) || num < 0) {
                errors.push('Please enter a valid positive number');
            }
        }

        if (field.tagName === 'TEXTAREA' && field.value.length > 1000) {
            errors.push('Description must be less than 1000 characters');
        }

        // Display errors
        if (errors.length > 0) {
            errorSpan.textContent = errors[0];
            field.classList.add('error');
        } else {
            errorSpan.textContent = '';
            field.classList.remove('error');
        }

        return errors.length === 0;
    }

    // Validate email
    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    // Clear validation errors
    function clearValidationErrors() {
        document.querySelectorAll('.field-error').forEach(span => {
            span.textContent = '';
        });
        document.querySelectorAll('.error').forEach(field => {
            field.classList.remove('error');
        });
        validationMessages.innerHTML = '';
    }

    // Handle form submission
    function handleFormSubmit(e) {
        e.preventDefault();

        clearValidationErrors();

        // Validate all fields
        let isValid = true;
        const formData = new FormData(contextForm);

        // Validate context type
        if (!contextTypeSelect.value) {
            showFieldError('context-type', 'Please select a context type');
            isValid = false;
        }

        // Validate required dynamic fields
        dynamicFieldsContainer.querySelectorAll('[required]').forEach(field => {
            if (!validateField(field)) {
                isValid = false;
            }
        });

        // Validate at least one feature is selected
        const selectedFeatures = Array.from(featureCheckboxes.querySelectorAll('input:checked')).map(cb => cb.value);
        if (selectedFeatures.length === 0 && featureCheckboxesGroup.style.display !== 'none') {
            showFieldError('features', 'Please select at least one feature');
            isValid = false;
        }

        if (!isValid) {
            showValidationError('Please fix the errors below');
            return;
        }

        // Prepare form data
        const data = {
            file_id: fileId,
            context_type: contextTypeSelect.value,
            description: descriptionField.value,
            features: selectedFeatures
        };

        // Add dynamic field values
        dynamicFieldsContainer.querySelectorAll('input, select, textarea').forEach(field => {
            if (field.type === 'checkbox') {
                if (field.checked) {
                    data[field.name] = field.value;
                }
            } else {
                if (field.value) {
                    data[field.name] = field.value;
                }
            }
        });

        // Submit form
        submitForm(data);
    }

    // Show field error
    function showFieldError(fieldName, message) {
        const errorSpan = document.getElementById(`${fieldName}-error`);
        if (errorSpan) {
            errorSpan.textContent = message;
        }
        const field = document.getElementById(fieldName) || document.querySelector(`[name="${fieldName}"]`);
        if (field) {
            field.classList.add('error');
        }
    }

    // Show validation error
    function showValidationError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-error';
        errorDiv.textContent = message;
        validationMessages.appendChild(errorDiv);
        validationMessages.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Submit form
    async function submitForm(data) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Processing...';

        try {
            const response = await fetch(contextForm.action, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                // Redirect to next page
                if (result.redirect_url) {
                    window.location.href = result.redirect_url;
                } else if (result.task_id) {
                    window.location.href = `/progress/${result.task_id}`;
                } else {
                    window.location.href = '/';
                }
            } else {
                showValidationError(result.message || 'An error occurred. Please try again.');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Continue';
            }
        } catch (error) {
            console.error('Error submitting form:', error);
            showValidationError('Network error. Please check your connection and try again.');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Continue';
        }
    }
});
