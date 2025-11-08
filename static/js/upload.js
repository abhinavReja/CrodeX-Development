// Upload handling JavaScript with ZIP validation and progress bar

document.addEventListener('DOMContentLoaded', function() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const uploadForm = document.getElementById('upload-form');
    const uploadPreview = document.getElementById('upload-preview');
    const uploadPlaceholder = uploadArea.querySelector('.upload-placeholder');
    const fileName = document.getElementById('file-name');
    const fileSize = document.getElementById('file-size');
    const fileType = document.getElementById('file-type');
    const btnRemove = document.getElementById('btn-remove');
    const uploadBtn = document.getElementById('upload-btn');
    const validationMessages = document.getElementById('validation-messages');
    const uploadProgressContainer = document.getElementById('upload-progress-container');
    const uploadProgressFill = document.getElementById('upload-progress-fill');
    const uploadProgressText = document.getElementById('upload-progress-text');
    const uploadStatusText = document.getElementById('upload-status-text');

    // Configuration
    const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB in bytes
    const ALLOWED_TYPES = ['application/zip', 'application/x-zip-compressed'];
    const ALLOWED_EXTENSIONS = ['.zip'];

    // Drag and drop handlers
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    });

    // File input change handler
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });

    // Click on upload area to trigger file input
    uploadArea.addEventListener('click', function(e) {
        if (e.target !== fileInput && e.target !== btnRemove && e.target.parentElement !== btnRemove) {
            fileInput.click();
        }
    });

    // Remove file handler
    btnRemove.addEventListener('click', function(e) {
        e.stopPropagation();
        resetFileSelection();
    });

    // Validate ZIP file
    function validateZipFile(file) {
        const errors = [];

        // Check file type
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        const isValidExtension = ALLOWED_EXTENSIONS.includes(fileExtension);
        const isValidMimeType = ALLOWED_TYPES.includes(file.type) || file.type === '';

        if (!isValidExtension && !isValidMimeType) {
            errors.push('File must be a ZIP archive (.zip)');
        }

        // Check file size
        if (file.size === 0) {
            errors.push('File is empty');
        } else if (file.size > MAX_FILE_SIZE) {
            errors.push(`File size (${formatFileSize(file.size)}) exceeds maximum allowed size of ${formatFileSize(MAX_FILE_SIZE)}`);
        }

        // Additional ZIP validation - check magic bytes (optional but more secure)
        // This would require reading the file, which we'll do on server side

        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }

    // Handle file selection
    function handleFileSelection(file) {
        // Clear previous validation messages
        clearValidationMessages();

        // Validate file
        const validation = validateZipFile(file);

        if (!validation.isValid) {
            showValidationErrors(validation.errors);
            resetFileSelection();
            return;
        }

        // Update UI
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        fileType.textContent = 'ZIP Archive';
        
        uploadPlaceholder.style.display = 'none';
        uploadPreview.style.display = 'block';
        uploadBtn.disabled = false;

        // Show success message
        showValidationSuccess('File is valid and ready to upload');
    }

    // Reset file selection
    function resetFileSelection() {
        fileInput.value = '';
        uploadPlaceholder.style.display = 'block';
        uploadPreview.style.display = 'none';
        uploadBtn.disabled = true;
        clearValidationMessages();
        hideUploadProgress();
    }

    // Show validation errors
    function showValidationErrors(errors) {
        validationMessages.innerHTML = '';
        errors.forEach(error => {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-error';
            errorDiv.innerHTML = `<strong>Error:</strong> ${error}`;
            validationMessages.appendChild(errorDiv);
        });
    }

    // Show validation success
    function showValidationSuccess(message) {
        validationMessages.innerHTML = '';
        const successDiv = document.createElement('div');
        successDiv.className = 'alert alert-success';
        successDiv.innerHTML = `<strong>Success:</strong> ${message}`;
        validationMessages.appendChild(successDiv);
    }

    // Clear validation messages
    function clearValidationMessages() {
        validationMessages.innerHTML = '';
    }

    // Format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    // Show upload progress
    function showUploadProgress() {
        uploadProgressContainer.style.display = 'block';
        uploadProgressFill.style.width = '0%';
        uploadProgressText.textContent = '0%';
        uploadStatusText.textContent = 'Preparing upload...';
    }

    // Update upload progress
    function updateUploadProgress(percent, status) {
        uploadProgressFill.style.width = percent + '%';
        uploadProgressText.textContent = Math.round(percent) + '%';
        uploadStatusText.textContent = status || 'Uploading...';
    }

    // Hide upload progress
    function hideUploadProgress() {
        uploadProgressContainer.style.display = 'none';
    }

    // Form submission handler with AJAX upload
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();

        if (!fileInput.files || fileInput.files.length === 0) {
            showValidationErrors(['Please select a file to upload.']);
            return;
        }

        const file = fileInput.files[0];
        
        // Validate again before upload
        const validation = validateZipFile(file);
        if (!validation.isValid) {
            showValidationErrors(validation.errors);
            return;
        }

        // Show upload progress
        showUploadProgress();
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Uploading...';

        // Create FormData
        const formData = new FormData();
        formData.append('file', file);

        // Create XMLHttpRequest for progress tracking
        const xhr = new XMLHttpRequest();

        // Upload progress
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                updateUploadProgress(percentComplete, 'Uploading...');
            }
        });

        // Load complete
        xhr.addEventListener('load', function() {
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    updateUploadProgress(100, 'Upload complete!');
                    
                    // Redirect to next page (context form or progress)
                    setTimeout(function() {
                        if (response.redirect_url) {
                            window.location.href = response.redirect_url;
                        } else if (response.file_id) {
                            window.location.href = `/context/${response.file_id}`;
                        } else {
                            window.location.href = '/';
                        }
                    }, 500);
                } catch (error) {
                    console.error('Error parsing response:', error);
                    showValidationErrors(['Upload failed. Please try again.']);
                    resetUploadState();
                }
            } else {
                try {
                    const error = JSON.parse(xhr.responseText);
                    showValidationErrors([error.message || 'Upload failed. Please try again.']);
                } catch (e) {
                    showValidationErrors([`Upload failed with status ${xhr.status}. Please try again.`]);
                }
                resetUploadState();
            }
        });

        // Error handling
        xhr.addEventListener('error', function() {
            showValidationErrors(['Network error. Please check your connection and try again.']);
            resetUploadState();
        });

        // Abort handling
        xhr.addEventListener('abort', function() {
            showValidationErrors(['Upload cancelled.']);
            resetUploadState();
        });

        // Send request
        xhr.open('POST', uploadForm.action);
        xhr.send(formData);
    });

    // Reset upload state
    function resetUploadState() {
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload File';
        hideUploadProgress();
    }

    // Prevent default drag behaviors on document
    document.addEventListener('dragover', function(e) {
        e.preventDefault();
    });

    document.addEventListener('drop', function(e) {
        e.preventDefault();
    });
});

