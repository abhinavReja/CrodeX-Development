// API Client - Centralized API communication

const API_BASE_URL = '/api';

class APIClient {
    /**
     * Make a fetch request with error handling
     */
    async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || `HTTP error! status: ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    /**
     * Upload a file
     */
    async uploadFile(file, onProgress) {
        const formData = new FormData();
        formData.append('file', file);

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable && onProgress) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    onProgress(percentComplete);
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (error) {
                        reject(new Error('Invalid response from server'));
                    }
                } else {
                    reject(new Error(`Upload failed with status: ${xhr.status}`));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed'));
            });

            xhr.open('POST', `${API_BASE_URL}/upload`);
            xhr.send(formData);
        });
    }

    /**
     * Submit context form
     */
    async submitContext(fileId, contextData) {
        return this.request('/context', {
            method: 'POST',
            body: JSON.stringify({
                file_id: fileId,
                ...contextData
            })
        });
    }

    /**
     * Get progress status
     */
    async getProgress(taskId) {
        return this.request(`/progress/${taskId}`);
    }

    /**
     * Cancel a task
     */
    async cancelTask(taskId) {
        return this.request(`/cancel/${taskId}`, {
            method: 'POST'
        });
    }

    /**
     * Download file
     */
    async downloadFile(fileId) {
        const response = await fetch(`${API_BASE_URL}/download/${fileId}`);
        if (!response.ok) {
            throw new Error('Download failed');
        }
        return response.blob();
    }

    /**
     * Get file info
     */
    async getFileInfo(fileId) {
        return this.request(`/file/${fileId}`);
    }
}

// Create singleton instance
const apiClient = new APIClient();

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = apiClient;
}

