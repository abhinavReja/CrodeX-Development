// Enhanced Progress Tracking with Real-time Updates (SSE), File-by-File Progress, Error Display, and Download Trigger

document.addEventListener('DOMContentLoaded', function() {
    const progressFill = document.getElementById('progress-fill');
    const progressPercentage = document.getElementById('progress-percentage');
    const statusCurrent = document.getElementById('status-current');
    const statusText = statusCurrent.querySelector('.status-text');
    const statusIcon = statusCurrent.querySelector('.status-icon');
    const statusTime = document.getElementById('status-time');
    const cancelBtn = document.getElementById('cancel-btn');
    const downloadBtn = document.getElementById('download-btn');
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    const errorDetails = document.getElementById('error-details');
    const filesProgressContainer = document.getElementById('files-progress-container');
    const filesList = document.getElementById('files-list');
    const filesCount = document.getElementById('files-count');
    const logContent = document.getElementById('log-content');
    const logEntries = document.getElementById('log-entries');
    const logToggleBtn = document.getElementById('log-toggle-btn');
    const retryBtn = document.getElementById('retry-btn');
    const cancelErrorBtn = document.getElementById('cancel-error-btn');

    let eventSource = null;
    let currentProgress = 0;
    let isCompleted = false;
    let isFailed = false;
    let filesData = [];
    let startTime = Date.now();
    let logEntriesCount = 0;

    // Initialize progress tracking
    if (typeof taskId !== 'undefined') {
        initializeProgressTracking(taskId);
    }

    // Initialize progress tracking with SSE
    function initializeProgressTracking(taskId) {
        // Try to use Server-Sent Events (SSE) for real-time updates
        if (typeof EventSource !== 'undefined') {
            startSSEConnection(taskId);
        } else {
            // Fallback to polling if SSE is not supported
            startPolling(taskId);
        }

        // Update elapsed time every second
        setInterval(updateElapsedTime, 1000);
    }

    // Start SSE connection
    function startSSEConnection(taskId) {
        try {
            eventSource = new EventSource(`/api/progress/stream/${taskId}`);

            eventSource.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    handleProgressUpdate(data);
                } catch (error) {
                    console.error('Error parsing SSE message:', error);
                }
            };

            eventSource.onerror = function(error) {
                console.error('SSE connection error:', error);
                // Fallback to polling on error
                if (eventSource) {
                    eventSource.close();
                }
                startPolling(taskId);
            };

            eventSource.onopen = function() {
                addLogEntry('Connected to real-time updates', 'info');
            };
        } catch (error) {
            console.error('Error establishing SSE connection:', error);
            // Fallback to polling
            startPolling(taskId);
        }
    }

    // Start polling as fallback
    function startPolling(taskId) {
        addLogEntry('Using polling for updates', 'info');
        const pollInterval = setInterval(async function() {
            if (isCompleted || isFailed) {
                clearInterval(pollInterval);
                return;
            }
            await fetchProgress(taskId);
        }, 2000); // Poll every 2 seconds
        // Initial fetch
        fetchProgress(taskId);
    }

    // Fetch progress from API (fallback method)
    async function fetchProgress(taskId) {
        try {
            const response = await fetch(`/api/progress/${taskId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            handleProgressUpdate(data);
        } catch (error) {
            console.error('Error fetching progress:', error);
            addLogEntry('Error fetching progress: ' + error.message, 'error');
        }
    }

    // Handle progress update
    function handleProgressUpdate(data) {
        // Update overall progress
        if (data.progress !== undefined) {
            updateProgress(data.progress, data.status_message || 'Processing...', getStatusIcon(data.status));
        }

        // Update status
        if (data.status) {
            updateStatus(data.status, data.status_message);
        }

        // Update steps
        if (data.step !== undefined) {
            updateSteps(data.step);
        }

        // Update file-by-file progress
        if (data.files && Array.isArray(data.files)) {
            updateFilesProgress(data.files);
        }

        // Add log entry
        if (data.log_message) {
            addLogEntry(data.log_message, data.log_level || 'info');
        }

        // Handle completion
        if (data.status === 'completed') {
            handleCompletion(data);
        } else if (data.status === 'failed') {
            handleFailure(data);
        }

        // Handle file processing updates
        if (data.file_update) {
            handleFileUpdate(data.file_update);
        }
    }

    // Update progress UI
    function updateProgress(percentage, status, icon) {
        currentProgress = Math.min(100, Math.max(0, percentage));
        progressFill.style.width = currentProgress + '%';
        progressPercentage.textContent = Math.round(currentProgress) + '%';
        statusText.textContent = status;
        statusIcon.textContent = icon;
    }

    // Update status
    function updateStatus(status, message) {
        statusText.textContent = message || getStatusMessage(status);
        statusIcon.textContent = getStatusIcon(status);
    }

    // Get status icon
    function getStatusIcon(status) {
        const icons = {
            'pending': '⏳',
            'processing': '⚙️',
            'converting': '🔄',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '🚫'
        };
        return icons[status] || '⏳';
    }

    // Get status message
    function getStatusMessage(status) {
        const messages = {
            'pending': 'Waiting to start...',
            'processing': 'Processing files...',
            'converting': 'Converting files...',
            'completed': 'Processing completed!',
            'failed': 'Processing failed',
            'cancelled': 'Processing cancelled'
        };
        return messages[status] || 'Processing...';
    }

    // Update step indicators
    function updateSteps(currentStep) {
        for (let i = 1; i <= 4; i++) {
            const step = document.getElementById(`step-${i}`);
            if (step) {
                const stepIcon = step.querySelector('.step-icon');
                step.classList.remove('active', 'completed');
                if (i < currentStep) {
                    step.classList.add('completed');
                    // Show checkmark when completed
                    if (stepIcon) {
                        stepIcon.textContent = '✓';
                        stepIcon.style.fontSize = '1.5rem';
                    }
                } else if (i === currentStep) {
                    step.classList.add('active');
                    // Show step number when active
                    if (stepIcon) {
                        stepIcon.textContent = i;
                        stepIcon.style.fontSize = '1.125rem';
                    }
                } else {
                    // Show step number for pending steps
                    if (stepIcon) {
                        stepIcon.textContent = i;
                        stepIcon.style.fontSize = '1.125rem';
                    }
                }
            }
        }
    }

    // Update files progress
    function updateFilesProgress(files) {
        filesData = files;
        filesProgressContainer.style.display = 'block';
        
        // Update files count
        const totalFiles = files.length;
        const completedFiles = files.filter(f => f.status === 'completed').length;
        filesCount.textContent = `${completedFiles} / ${totalFiles} files processed`;

        // Clear and rebuild files list
        filesList.innerHTML = '';

        files.forEach((file, index) => {
            const fileItem = createFileProgressItem(file, index);
            filesList.appendChild(fileItem);
        });
    }

    // Create file progress item
    function createFileProgressItem(file, index) {
        const div = document.createElement('div');
        div.className = `file-progress-item ${file.status}`;
        div.setAttribute('data-file-id', file.id || index);

        const fileIcon = getFileIcon(file.status);
        const progressPercent = file.progress || (file.status === 'completed' ? 100 : 0);

        div.innerHTML = `
            <div class="file-info">
                <span class="file-icon">${fileIcon}</span>
                <div class="file-details">
                    <div class="file-name">${escapeHtml(file.name || `File ${index + 1}`)}</div>
                    <div class="file-status">${getFileStatusText(file.status)}</div>
                </div>
                <div class="file-progress-percent">${Math.round(progressPercent)}%</div>
            </div>
            <div class="file-progress-bar">
                <div class="file-progress-fill" style="width: ${progressPercent}%"></div>
            </div>
            ${file.error ? `<div class="file-error">${escapeHtml(file.error)}</div>` : ''}
        `;

        return div;
    }

    // Get file icon
    function getFileIcon(status) {
        const icons = {
            'pending': '⏳',
            'processing': '⚙️',
            'completed': '✅',
            'failed': '❌',
            'skipped': '⏭️'
        };
        return icons[status] || '📄';
    }

    // Get file status text
    function getFileStatusText(status) {
        const texts = {
            'pending': 'Waiting...',
            'processing': 'Processing...',
            'completed': 'Completed',
            'failed': 'Failed',
            'skipped': 'Skipped'
        };
        return texts[status] || status;
    }

    // Handle file update
    function handleFileUpdate(fileUpdate) {
        const fileItem = filesList.querySelector(`[data-file-id="${fileUpdate.id}"]`);
        if (fileItem) {
            // Update existing file item
            const file = filesData.find(f => f.id === fileUpdate.id);
            if (file) {
                Object.assign(file, fileUpdate);
                const newItem = createFileProgressItem(file, filesData.indexOf(file));
                fileItem.replaceWith(newItem);
            }
        } else {
            // Add new file if it doesn't exist
            filesData.push(fileUpdate);
            updateFilesProgress(filesData);
        }
    }

    // Handle completion
    function handleCompletion(data) {
        isCompleted = true;
        updateProgress(100, 'Completed', '✅');
        updateSteps(4);
        stopProgressTracking();
        addLogEntry('Processing completed successfully', 'success');
        
        // Show download button
        downloadBtn.style.display = 'inline-block';
        cancelBtn.style.display = 'none';

        // Set download URL
        if (data.file_id) {
            downloadBtn.onclick = function() {
                window.location.href = `/download/${data.file_id}`;
            };
        } else if (data.download_url) {
            downloadBtn.onclick = function() {
                window.location.href = data.download_url;
            };
        }

        // Auto-redirect after delay if no user interaction
        setTimeout(function() {
            if (!downloadBtn.matches(':hover')) {
                if (data.file_id) {
                    window.location.href = `/download/${data.file_id}`;
                }
            }
        }, 5000);
    }

    // Handle failure
    function handleFailure(data) {
        isFailed = true;
        updateProgress(data.progress || 0, 'Failed', '❌');
        stopProgressTracking();
        showError(data.message || 'Processing failed', data.error_details);
        addLogEntry('Processing failed: ' + (data.message || 'Unknown error'), 'error');
        cancelBtn.style.display = 'none';
    }

    // Show error
    function showError(message, details) {
        errorMessage.textContent = message;
        
        if (details) {
            if (typeof details === 'string') {
                errorDetails.textContent = details;
            } else if (Array.isArray(details)) {
                errorDetails.innerHTML = '<ul>' + details.map(d => `<li>${escapeHtml(d)}</li>`).join('') + '</ul>';
            } else if (typeof details === 'object') {
                errorDetails.innerHTML = '<pre>' + JSON.stringify(details, null, 2) + '</pre>';
            }
            errorDetails.style.display = 'block';
        } else {
            errorDetails.style.display = 'none';
        }

        errorContainer.style.display = 'block';
        errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Add log entry
    function addLogEntry(message, level = 'info') {
        logEntriesCount++;
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${level}`;
        logEntry.innerHTML = `
            <span class="log-time">[${timestamp}]</span>
            <span class="log-level">[${level.toUpperCase()}]</span>
            <span class="log-message">${escapeHtml(message)}</span>
        `;
        logEntries.appendChild(logEntry);
        
        // Auto-scroll to bottom
        logEntries.scrollTop = logEntries.scrollHeight;

        // Keep only last 100 entries
        if (logEntriesCount > 100) {
            const firstEntry = logEntries.firstElementChild;
            if (firstEntry) {
                firstEntry.remove();
                logEntriesCount--;
            }
        }
    }

    // Update elapsed time
    function updateElapsedTime() {
        if (isCompleted || isFailed) return;
        
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        statusTime.textContent = `Elapsed: ${minutes}m ${seconds}s`;
    }

    // Stop progress tracking
    function stopProgressTracking() {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
    }

    // Escape HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Cancel button handler
    cancelBtn.addEventListener('click', function() {
        if (confirm('Are you sure you want to cancel the processing?')) {
            stopProgressTracking();
            fetch(`/api/cancel/${taskId}`, { method: 'POST' })
                .then(() => {
                    addLogEntry('Processing cancelled', 'info');
                    updateStatus('cancelled', 'Processing cancelled');
                    cancelBtn.style.display = 'none';
                })
                .catch(error => {
                    console.error('Error canceling task:', error);
                    addLogEntry('Error cancelling task: ' + error.message, 'error');
                });
        }
    });

    // Download button handler (already set in handleCompletion)
    
    // Retry button handler
    retryBtn.addEventListener('click', function() {
        errorContainer.style.display = 'none';
        isFailed = false;
        currentProgress = 0;
        startTime = Date.now();
        initializeProgressTracking(taskId);
    });

    // Cancel error button handler
    cancelErrorBtn.addEventListener('click', function() {
        window.location.href = '/';
    });

    // Log toggle button handler
    logToggleBtn.addEventListener('click', function() {
        if (logContent.style.display === 'none') {
            logContent.style.display = 'block';
            logToggleBtn.textContent = 'Hide';
        } else {
            logContent.style.display = 'none';
            logToggleBtn.textContent = 'Show';
        }
    });

    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        stopProgressTracking();
    });
});
