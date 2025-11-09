// Download/Result page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const copyLinkBtn = document.getElementById('copy-link-btn');
    const emailBtn = document.getElementById('email-btn');
    const downloadZipBtn = document.getElementById('download-zip');
    const downloadGuideBtn = document.getElementById('download-guide');
    const resultSummary = document.getElementById('result-summary');
    const sourceFrameworkEl = document.getElementById('source-framework');
    const targetFrameworkEl = document.getElementById('target-framework');
    const filesCountEl = document.getElementById('files-count');

    // Load result summary from state
    loadResultSummary();

    // Copy link functionality
    if (copyLinkBtn) {
        copyLinkBtn.addEventListener('click', function() {
            const currentUrl = window.location.href;
            
            // Use Utils.copyToClipboard if available, otherwise use native API
            if (typeof copyToClipboard === 'function') {
                copyToClipboard(currentUrl);
            } else if (typeof Utils !== 'undefined' && Utils.copyToClipboard) {
                Utils.copyToClipboard(currentUrl);
            } else {
                // Fallback to native clipboard API
                navigator.clipboard.writeText(currentUrl).then(function() {
                    showToast('Link copied to clipboard!', 'success');
                }).catch(function(err) {
                    console.error('Failed to copy link:', err);
                    showToast('Failed to copy link', 'error');
                });
            }
        });
    }

    // Email functionality
    if (emailBtn) {
        emailBtn.addEventListener('click', function() {
            const subject = encodeURIComponent('Your converted project is ready');
            const body = encodeURIComponent(`Your project has been converted and is ready for download.\n\nDownload link: ${window.location.href}`);
            const mailtoLink = `mailto:?subject=${subject}&body=${body}`;
            
            window.location.href = mailtoLink;
        });
    }

    // Download ZIP button (already has href, just track click)
    if (downloadZipBtn) {
        downloadZipBtn.addEventListener('click', function() {
            console.log('Download ZIP initiated for file:', typeof fileId !== 'undefined' ? fileId : 'unknown');
            // Optional: Track download event
        });
    }

    // Download Migration Guide button
    if (downloadGuideBtn) {
        downloadGuideBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Check if guide URL exists in state or use fallback
            const conversionResult = State.getConversionResult();
            const guideUrl = conversionResult?.guide_url || conversionResult?.guideUrl || '#';
            
            if (guideUrl && guideUrl !== '#') {
                window.location.href = guideUrl;
            } else {
                // Generate or download migration guide
                generateMigrationGuide();
            }
        });
    }
});

function loadResultSummary() {
    const sourceFrameworkEl = document.getElementById('source-framework');
    const targetFrameworkEl = document.getElementById('target-framework');
    const filesCountEl = document.getElementById('files-count');
    
    const analysis = State.getAnalysis();
    const targetFramework = State.getTargetFramework();
    const conversionResult = State.getConversionResult();
    
    // Get source framework from analysis
    const sourceFramework = analysis?.framework || 'Source Framework';
    
    // Get target framework
    const targetFrameworkName = targetFramework || 'Target Framework';
    
    // Get files processed count from conversion result or use default
    let filesProcessed = 0;
    if (conversionResult) {
        filesProcessed = conversionResult.files_processed || 
                        conversionResult.filesProcessed || 
                        (conversionResult.files && conversionResult.files.length) || 
                        0;
    }
    
    // If filesProcessed is still 0, try to get from task info if available
    // This would be set if the page was loaded from conversion completion
    if (filesProcessed === 0 && typeof files_processed !== 'undefined') {
        filesProcessed = files_processed;
    }
    
    // Update UI elements
    if (sourceFrameworkEl) {
        // Extract framework name (remove version if present)
        const frameworkName = sourceFramework.split(' ')[0];
        sourceFrameworkEl.textContent = frameworkName;
    }
    
    if (targetFrameworkEl) {
        targetFrameworkEl.textContent = targetFrameworkName;
    }
    
    if (filesCountEl) {
        filesCountEl.textContent = filesProcessed;
    }
}

function generateMigrationGuide() {
    // This would typically generate or fetch a migration guide
    // For now, we'll create a simple text file
    const analysis = State.getAnalysis();
    const context = State.getContext();
    const targetFramework = State.getTargetFramework();
    
    const guideContent = generateGuideContent(analysis, context, targetFramework);
    downloadTextFile(guideContent, 'migration_guide.md', 'text/markdown');
}

function generateGuideContent(analysis, context, targetFramework) {
    const sourceFramework = analysis?.framework || 'Source Framework';
    const lines = [];
    
    lines.push(`# Migration Guide: ${sourceFramework} → ${targetFramework}`);
    lines.push('');
    lines.push('## Overview');
    lines.push('');
    lines.push(`This guide will help you migrate your project from ${sourceFramework} to ${targetFramework}.`);
    lines.push('');
    lines.push('## Project Information');
    lines.push('');
    if (context?.purpose) {
        lines.push(`**Purpose:** ${context.purpose}`);
        lines.push('');
    }
    if (context?.features && context.features.length > 0) {
        lines.push('**Key Features:**');
        context.features.forEach(feature => {
            lines.push(`- ${feature}`);
        });
        lines.push('');
    }
    lines.push('## Migration Steps');
    lines.push('');
    lines.push('1. Review the converted code structure');
    lines.push('2. Update dependencies and configuration');
    lines.push('3. Test all functionality');
    lines.push('4. Update documentation');
    lines.push('');
    lines.push('## Notes');
    lines.push('');
    if (analysis?.notes) {
        lines.push(analysis.notes);
        lines.push('');
    }
    lines.push('## Files Requiring Manual Review');
    lines.push('');
    lines.push('- Configuration files may need manual adjustment');
    lines.push('- Database migrations may require updates');
    lines.push('- Test files should be reviewed and updated');
    lines.push('');
    
    return lines.join('\n');
}

function downloadTextFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast('Migration guide downloaded', 'success');
}

// Export functions to window
window.loadResultSummary = loadResultSummary;
window.generateMigrationGuide = generateMigrationGuide;
