// Download page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const copyLinkBtn = document.getElementById('copy-link-btn');
    const emailBtn = document.getElementById('email-btn');
    const downloadBtn = document.getElementById('download-btn');

    // Copy link functionality
    if (copyLinkBtn) {
        copyLinkBtn.addEventListener('click', function() {
            const currentUrl = window.location.href;
            
            // Copy to clipboard
            navigator.clipboard.writeText(currentUrl).then(function() {
                // Show success message
                const originalText = copyLinkBtn.textContent;
                copyLinkBtn.textContent = 'Link Copied!';
                copyLinkBtn.style.backgroundColor = '#28a745';
                copyLinkBtn.style.borderColor = '#28a745';
                copyLinkBtn.style.color = '#fff';
                
                setTimeout(function() {
                    copyLinkBtn.textContent = originalText;
                    copyLinkBtn.style.backgroundColor = '';
                    copyLinkBtn.style.borderColor = '';
                    copyLinkBtn.style.color = '';
                }, 2000);
            }).catch(function(err) {
                console.error('Failed to copy link:', err);
                alert('Failed to copy link. Please copy it manually.');
            });
        });
    }

    // Email functionality
    if (emailBtn) {
        emailBtn.addEventListener('click', function() {
            const subject = encodeURIComponent('Your processed file is ready');
            const body = encodeURIComponent(`Your file has been processed and is ready for download.\n\nDownload link: ${window.location.href}`);
            const mailtoLink = `mailto:?subject=${subject}&body=${body}`;
            
            window.location.href = mailtoLink;
        });
    }

    // Download button click tracking (optional)
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            // Optional: Track download event
            console.log('Download initiated for file:', typeof fileId !== 'undefined' ? fileId : 'unknown');
        });
    }
});

