// Utility functions for toast notifications and loading overlay

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of toast (success, error, warning, info)
 * @param {number} timeout - Timeout in milliseconds (default: 3000)
 */
function showToast(message, type = "success", timeout = 3000) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    const icon = toast.querySelector(".toast-icon");
    if (icon) {
        const map = {
            success: "fa-check-circle",
            error: "fa-exclamation-circle",
            warning: "fa-exclamation-triangle",
            info: "fa-info-circle"
        };
        icon.className = `toast-icon fas ${map[type] || map.success}`;
    }
    
    toast.classList.remove("hidden", "success", "error", "warning", "info");
    toast.classList.add(type);
    
    const messageEl = document.getElementById('toast-message');
    if (messageEl) {
        messageEl.textContent = message;
    }
    
    toast.style.display = "flex";
    
    // Clear existing timer
    if (window.__toastTimer) {
        clearTimeout(window.__toastTimer);
    }
    
    // Auto-hide after timeout
    window.__toastTimer = setTimeout(() => {
        hideToast();
    }, timeout);
}

/**
 * Hide toast notification
 */
function hideToast() {
    const toast = document.getElementById('toast');
    if (toast) {
        toast.style.display = "none";
        toast.classList.add("hidden");
    }
}

/**
 * Show loading overlay
 * @param {string} message - Loading message (default: "Processing...")
 */
function showLoading(message = "Processing...") {
    const overlay = document.getElementById('loading-overlay');
    if (!overlay) return;
    
    overlay.classList.remove("hidden");
    const p = overlay.querySelector("p");
    if (p) {
        p.textContent = message;
    }
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add("hidden");
    }
}

/**
 * Format bytes to human-readable format
 * @param {number} bytes - Bytes to format
 * @returns {string} Formatted string
 */
function formatBytes(bytes) {
    if (isNaN(bytes)) return "0 B";
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    if (bytes === 0) return "0 B";
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    const val = (bytes / Math.pow(1024, i)).toFixed(2);
    return `${val} ${sizes[i]}`;
}

/**
 * Format duration in seconds to MM:SS format
 * @param {number} totalSeconds - Total seconds
 * @returns {string} Formatted duration
 */
function formatDuration(totalSeconds) {
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
}

/**
 * Set progress bar width
 * @param {HTMLElement} el - Progress bar element
 * @param {number} percent - Percentage (0-100)
 */
function setProgress(el, percent) {
    if (!el) return;
    el.style.width = `${Math.max(0, Math.min(percent, 100))}%`;
}

/**
 * Navigate to URL
 * @param {string} url - URL to navigate to
 */
function navigate(url) {
    window.location.href = url;
}

/**
 * Format date string
 * @param {string} dateString - Date string
 * @returns {string} Formatted date
 */
function formatDate(dateString) {
    const d = new Date(dateString);
    return `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`;
}

/**
 * Debounce function
 * @param {Function} fn - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(fn, wait) {
    let t;
    return function(...args) {
        clearTimeout(t);
        t = setTimeout(() => fn.apply(this, args), wait);
    };
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast("Copied to clipboard", "success");
    } catch(err) {
        console.error(err);
        showToast("Failed to copy", "error");
    }
}

/**
 * Download file from URL
 * @param {string} url - File URL
 * @param {string} filename - Filename
 */
function downloadFile(url, filename) {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

/**
 * Scroll to anchor on page load (handles navigation from other pages)
 */
function scrollToAnchor() {
    // Check if URL has a hash
    if (window.location.hash) {
        const hash = window.location.hash.substring(1); // Remove the #
        const element = document.getElementById(hash);
        
        if (element) {
            // Wait for page to be fully loaded
            setTimeout(() => {
                const offset = 80; // Offset for navbar height
                const elementPosition = element.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - offset;
                
                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }, 100);
        }
    }
}

// Run on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scrollToAnchor);
} else {
    scrollToAnchor();
}

// Export functions to window for global access
window.showToast = showToast;
window.hideToast = hideToast;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.formatBytes = formatBytes;
window.formatDuration = formatDuration;
window.setProgress = setProgress;
window.navigate = navigate;
window.formatDate = formatDate;
window.debounce = debounce;
window.copyToClipboard = copyToClipboard;
window.downloadFile = downloadFile;
window.scrollToAnchor = scrollToAnchor;

// Create Utils object for organized access
window.Utils = {
    showToast,
    hideToast,
    showLoading,
    hideLoading,
    formatBytes,
    formatDuration,
    setProgress,
    navigate,
    formatDate,
    debounce,
    copyToClipboard,
    downloadFile
};

