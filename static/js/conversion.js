// Conversion/Progress page JavaScript with real-time updates

let conversionStartTime = null;
let timerInterval = null;
let progressPollInterval = null;
let eventSource = null;
let filesProcessed = 0;
let warningsCount = 0;

const sourceIcon = document.getElementById('source-icon');
const targetIcon = document.getElementById('target-icon');
const currentStage = document.getElementById('current-stage');
const overallPercent = document.getElementById('overall-percent');
const mainProgressFill = document.getElementById('main-progress-fill');
const currentMessage = document.getElementById('current-message');
const conversionLog = document.getElementById('conversion-log');
const filesProcessedEl = document.getElementById('files-processed');
const timeElapsedEl = document.getElementById('time-elapsed');
const warningsCountEl = document.getElementById('warnings-count');
const errorContainer = document.getElementById('error-container');
const errorMessage = document.getElementById('error-message');
const errorDetails = document.getElementById('error-details');
const retryBtn = document.getElementById('retry-btn');
const cancelErrorBtn = document.getElementById('cancel-error-btn');

document.addEventListener('DOMContentLoaded', () => {
    setupIcons();
    startTimer();
    
    // Setup error handlers
    if (retryBtn) {
        retryBtn.addEventListener('click', handleRetry);
    }
    if (cancelErrorBtn) {
        cancelErrorBtn.addEventListener('click', () => {
            window.location.href = '/';
        });
    }
    
    // Start conversion tracking
    // Get project_id from template variable (window.projectId) or extract from URL
    let projectId = null;
    
    // First, try to get projectId from window (set by template in progress.html)
    if (typeof window.projectId !== 'undefined' && window.projectId) {
        projectId = window.projectId;
    } else {
        // Extract from URL path (e.g., /progress/3c8849c0-e95e-4ecd-b2f3-d32d0e602f26)
        const pathParts = window.location.pathname.split('/').filter(part => part);
        const progressIndex = pathParts.indexOf('progress');
        if (progressIndex !== -1 && pathParts[progressIndex + 1]) {
            projectId = pathParts[progressIndex + 1];
        } else if (pathParts.length > 0) {
            // Fallback: use last part of path
            projectId = pathParts[pathParts.length - 1];
        }
    }
    
    // Validate projectId
    if (projectId && projectId !== 'progress' && projectId !== '') {
        startConversion(projectId);
    } else {
        addLogEntry('No project ID found. Please upload a file first.', 'error');
        showError('No project found', 'Please start by uploading a file.');
    }
});

function setupIcons() {
    const analysis = State.getAnalysis();
    const targetFramework = State.getTargetFramework();
    
    if (analysis && analysis.framework) {
        const icon = getFrameworkIcon(analysis.framework);
        if (sourceIcon) {
            sourceIcon.innerHTML = `<i class="${icon}"></i>`;
        }
    }
    
    if (targetFramework) {
        const icon = getFrameworkIcon(targetFramework);
        if (targetIcon) {
            targetIcon.innerHTML = `<i class="${icon}"></i>`;
        }
    }
}

function getFrameworkIcon(framework) {
    const icons = {
        'Laravel': 'fab fa-laravel',
        'Django': 'fab fa-python',
        'Flask': 'fab fa-python',
        'Express.js': 'fab fa-node-js',
        'Spring Boot': 'fab fa-java',
        'ASP.NET Core': 'fab fa-microsoft',
        'Symfony': 'fab fa-symfony',
        'CodeIgniter': 'fab fa-php'
    };
    
    if (framework) {
        const key = Object.keys(icons).find(k => 
            framework.toLowerCase().startsWith(k.toLowerCase())
        );
        if (key) {
            return icons[key];
        }
    }
    
    return 'fas fa-code';
}

async function startConversion(projectId) {
    if (!projectId) {
        addLogEntry('No project ID found', 'error');
        showError('No project ID', 'Please upload a file first.');
        return;
    }
    
    conversionStartTime = Date.now();
    addLogEntry('Starting conversion process...', 'info');
    
    // Check if conversion is already in progress or completed
    try {
        const statusResponse = await fetch(`/api/conversion-progress/${projectId}`);
        if (statusResponse.ok) {
            const statusData = await statusResponse.json();
            if (statusData.status === 'success' && statusData.progress) {
                const progress = statusData.progress;
                if (progress.complete) {
                    addLogEntry('Conversion already completed', 'success');
                    handleConversionComplete({ project_id: projectId });
                    return;
                } else if (progress.percentage > 0) {
                    addLogEntry('Conversion already in progress', 'info');
                    startProgressPolling(projectId);
                    return;
                }
            }
        }
    } catch (error) {
        console.error('Error checking conversion status:', error);
    }
    
    // Auto-start conversion if context is confirmed
    try {
        // Trigger conversion start (target_framework is in session context)
        const response = await fetch('/api/convert', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})  // Target framework is in session context
        });
        
        if (response.ok) {
            const result = await response.json();
            addLogEntry('Conversion process started', 'success');
            // Start tracking progress
            startProgressPolling(projectId);
        } else {
            const errorData = await response.json();
            addLogEntry('Error starting conversion: ' + (errorData.message || 'Unknown error'), 'error');
            handleConversionError(errorData.message || 'Conversion failed to start');
        }
    } catch (error) {
        console.error('Error starting conversion:', error);
        addLogEntry('Error starting conversion: ' + error.message, 'error');
        handleConversionError('Failed to start conversion: ' + error.message);
    }
}

function startProgressPolling(projectId) {
    if (!projectId) {
        addLogEntry('No project ID available for progress tracking', 'error');
        return;
    }
    
    addLogEntry('Starting progress tracking', 'info');
    
    // Clear any existing interval
    if (progressPollInterval) {
        clearInterval(progressPollInterval);
    }
    
    progressPollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/conversion-progress/${projectId}`);
            if (response.ok) {
                const result = await response.json();
                if (result.status === 'success' && result.progress) {
                    const progress = result.progress;
                    
                    // Convert progress data to format expected by handleProgressUpdate
                    const progressData = {
                        progress: progress.percentage || 0,
                        status: progress.stage || 'pending',
                        status_message: progress.message || 'Processing...',
                        complete: progress.complete || false,
                        error: progress.error
                    };
                    
                    handleProgressUpdate(progressData);
                    
                    if (progress.complete || progress.error) {
                        clearInterval(progressPollInterval);
                        if (progress.error) {
                            handleConversionError(progress.error);
                        } else {
                            handleConversionComplete({ project_id: projectId });
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Progress polling error:', error);
            addLogEntry('Error fetching progress: ' + error.message, 'error');
        }
    }, 2000);
    
    // Initial fetch
    fetch(`/api/conversion-progress/${projectId}`)
        .then(res => res.json())
        .then(result => {
            if (result.status === 'success' && result.progress) {
                const progress = result.progress;
                const progressData = {
                    progress: progress.percentage || 0,
                    status: progress.stage || 'pending',
                    status_message: progress.message || 'Processing...',
                    complete: progress.complete || false
                };
                handleProgressUpdate(progressData);
            }
        })
        .catch(err => {
            console.error('Error fetching initial progress:', err);
            addLogEntry('Error fetching progress: ' + err.message, 'error');
        });
}

function handleProgressUpdate(data) {
    // Update overall progress
    const percent = data.progress || 0;
    updateProgress(percent);
    
    // Update current stage and message
    if (data.status_message) {
        currentMessage.textContent = data.status_message;
    }
    
    if (data.status) {
        updateStageFromStatus(data.status, percent);
    }
    
    // Update files processed
    if (data.files_processed !== undefined) {
        filesProcessed = data.files_processed;
    } else if (data.files && Array.isArray(data.files)) {
        filesProcessed = data.files.filter(f => f.status === 'completed').length;
    }
    if (filesProcessedEl) {
        filesProcessedEl.textContent = filesProcessed;
    }
    
    // Update warnings
    if (data.warnings !== undefined) {
        warningsCount = data.warnings;
        if (warningsCountEl) {
            warningsCountEl.textContent = warningsCount;
        }
    }
    
    // Add log entry
    if (data.log_message) {
        addLogEntry(data.log_message, data.log_level || 'info');
    }
    
    // Handle completion
    if (data.status === 'completed') {
        handleConversionComplete(data);
    } else if (data.status === 'failed') {
        handleConversionError(data.message || 'Conversion failed', data.error_details);
    }
}

function updateProgress(percent) {
    const progress = Math.min(100, Math.max(0, percent));
    if (mainProgressFill) {
        mainProgressFill.style.width = progress + '%';
    }
    if (overallPercent) {
        overallPercent.textContent = `${Math.round(progress)}%`;
    }
}

function updateStageFromStatus(status, percent) {
    let stage = 'analysis';
    let stageTitle = 'Analyzing Project Structure';
    
    if (percent < 25) {
        stage = 'analysis';
        stageTitle = 'Deep Analysis';
    } else if (percent < 70) {
        stage = 'conversion';
        stageTitle = 'Code Conversion';
    } else if (percent < 90) {
        stage = 'documentation';
        stageTitle = 'Generating Documentation';
    } else {
        stage = 'finalization';
        stageTitle = 'Finalizing';
    }
    
    if (currentStage) {
        currentStage.textContent = stageTitle;
    }
    
    updateStageIndicators(stage, percent);
}

function updateStageIndicators(stageKey, percent) {
    const stages = {
        'analysis': { element: 'stage-analysis', threshold: 25 },
        'conversion': { element: 'stage-conversion', threshold: 70 },
        'documentation': { element: 'stage-documentation', threshold: 90 },
        'finalization': { element: 'stage-finalization', threshold: 100 }
    };
    
    const keys = Object.keys(stages);
    keys.forEach((k, idx) => {
        const el = document.getElementById(stages[k].element);
        if (!el) return;
        
        const icon = el.querySelector('.stage-icon');
        const fill = el.querySelector('.stage-progress-fill');
        const detail = el.querySelector('#conversion-detail');
        
        if (icon) {
            icon.classList.remove('pending', 'active', 'done');
        }
        
        const prevThreshold = idx > 0 ? stages[keys[idx - 1]].threshold : 0;
        let localPct = 0;
        
        if (percent >= stages[k].threshold) {
            if (icon) icon.classList.add('done');
            localPct = 100;
        } else if (k === stageKey) {
            if (icon) icon.classList.add('active');
            localPct = Math.max(0, Math.min(100, 
                Math.floor(((percent - prevThreshold) / (stages[k].threshold - prevThreshold)) * 100)
            ));
        } else {
            if (icon) icon.classList.add('pending');
            localPct = 0;
        }
        
        if (fill) {
            fill.style.width = `${localPct}%`;
        }
        
        // Update conversion detail message
        if (k === 'conversion' && detail) {
            if (percent >= stages[k].threshold) {
                detail.textContent = 'Files converted successfully';
            } else if (k === stageKey) {
                detail.textContent = `Converting files... ${Math.round(localPct)}%`;
            }
        }
    });
}

function handleConversionComplete(data) {
    clearInterval(timerInterval);
    clearInterval(progressPollInterval);
    if (eventSource) {
        eventSource.close();
    }
    
    addLogEntry('Conversion completed successfully!', 'success');
    updateProgress(100);
    updateStageIndicators('finalization', 100);
    
    if (currentStage) {
        currentStage.textContent = 'Conversion Complete!';
    }
    if (currentMessage) {
        currentMessage.textContent = 'Your project has been successfully converted';
    }
    
    showToast('Conversion completed successfully!', 'success');
    
    // Get project_id from data or extract from URL
    const projectId = data.project_id || data.file_id || window.location.pathname.split('/').pop();
    
    // Save conversion result to state for download page
    if (typeof State !== 'undefined') {
        State.setConversionResult({
            finished: true,
            project_id: projectId,
            files_processed: filesProcessed,
            warnings: warningsCount,
            completed_at: new Date().toISOString()
        });
    }
    
    // Redirect to download page after delay
    setTimeout(() => {
        if (projectId) {
            window.location.href = `/download/${projectId}`;
        } else {
            window.location.href = '/';
        }
    }, 2000);
}

function handleConversionError(error, details) {
    clearInterval(timerInterval);
    clearInterval(progressPollInterval);
    if (eventSource) {
        eventSource.close();
    }
    
    addLogEntry('Conversion failed: ' + error, 'error');
    showToast('Conversion failed: ' + error, 'error');
    
    if (currentStage) {
        currentStage.textContent = 'Conversion Failed';
    }
    if (currentMessage) {
        currentMessage.textContent = error;
    }
    
    showError(error, details);
}

function showError(message, details) {
    if (errorMessage) {
        errorMessage.textContent = message;
    }
    
    if (errorDetails && details) {
        if (typeof details === 'string') {
            errorDetails.textContent = details;
        } else if (Array.isArray(details)) {
            errorDetails.innerHTML = '<ul>' + details.map(d => `<li>${escapeHtml(d)}</li>`).join('') + '</ul>';
        } else if (typeof details === 'object') {
            errorDetails.innerHTML = '<pre>' + JSON.stringify(details, null, 2) + '</pre>';
        }
        errorDetails.style.display = 'block';
    } else if (errorDetails) {
        errorDetails.style.display = 'none';
    }
    
    if (errorContainer) {
        errorContainer.style.display = 'flex';
    }
}

function handleRetry() {
    if (errorContainer) {
        errorContainer.style.display = 'none';
    }
    conversionStartTime = Date.now();
    filesProcessed = 0;
    warningsCount = 0;
    
    // Get project_id from URL
    const projectId = window.location.pathname.split('/').pop();
    startConversion(projectId);
}

function startTimer() {
    timerInterval = setInterval(() => {
        if (conversionStartTime && timeElapsedEl) {
            const elapsed = Math.floor((Date.now() - conversionStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            timeElapsedEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
    }, 1000);
}

function addLogEntry(message, type = 'info') {
    if (!conversionLog) return;
    
    const timestamp = new Date().toLocaleTimeString();
    const iconClassMap = {
        info: 'fa-info-circle',
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle'
    };
    const colorClassMap = {
        info: 'text-info',
        success: 'text-success',
        error: 'text-error',
        warning: 'text-warning'
    };
    
    const entry = document.createElement('div');
    entry.className = `log-entry ${colorClassMap[type] || ''}`;
    entry.innerHTML = `
        <span class="log-time">[${timestamp}]</span>
        <i class="fas ${iconClassMap[type] || 'fa-info-circle'}"></i>
        <span class="log-message">${escapeHtml(message)}</span>
    `;
    
    conversionLog.appendChild(entry);
    conversionLog.scrollTop = conversionLog.scrollHeight;
    
    // Keep only last 100 entries
    while (conversionLog.children.length > 100) {
        conversionLog.removeChild(conversionLog.firstChild);
    }
}

function toggleLog() {
    if (!conversionLog) return;
    
    const button = event.currentTarget;
    const icon = button.querySelector('i');
    
    if (conversionLog.classList.contains('collapsed')) {
        conversionLog.classList.remove('collapsed');
        if (icon) {
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-up');
        }
    } else {
        conversionLog.classList.add('collapsed');
        if (icon) {
            icon.classList.remove('fa-chevron-up');
            icon.classList.add('fa-chevron-down');
        }
    }
}

window.toggleLog = toggleLog;

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (eventSource) {
        eventSource.close();
    }
    if (timerInterval) {
        clearInterval(timerInterval);
    }
    if (progressPollInterval) {
        clearInterval(progressPollInterval);
    }
});

