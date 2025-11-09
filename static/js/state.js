// State management using localStorage
const State = {
    KEYS: {
        PROJECT_ID: 'converter_project_id',
        FILE_ID: 'converter_file_id',
        ANALYSIS: 'converter_analysis',
        CONTEXT: 'converter_context',
        TARGET_FRAMEWORK: 'converter_target_framework',
        CONVERSION_RESULT: 'converter_result'
    },
    
    getProjectId() {
        return localStorage.getItem(this.KEYS.PROJECT_ID);
    },
    
    setProjectId(id) {
        localStorage.setItem(this.KEYS.PROJECT_ID, id);
    },
    
    getFileId() {
        return localStorage.getItem(this.KEYS.FILE_ID);
    },
    
    setFileId(id) {
        localStorage.setItem(this.KEYS.FILE_ID, id);
    },
    
    getAnalysis() {
        try {
            return JSON.parse(localStorage.getItem(this.KEYS.ANALYSIS) || "null");
        } catch(e) {
            return null;
        }
    },
    
    setAnalysis(a) {
        localStorage.setItem(this.KEYS.ANALYSIS, JSON.stringify(a || null));
    },
    
    getContext() {
        try {
            return JSON.parse(localStorage.getItem(this.KEYS.CONTEXT) || "null");
        } catch(e) {
            return null;
        }
    },
    
    setContext(c) {
        localStorage.setItem(this.KEYS.CONTEXT, JSON.stringify(c || null));
    },
    
    getTargetFramework() {
        return localStorage.getItem(this.KEYS.TARGET_FRAMEWORK);
    },
    
    setTargetFramework(f) {
        localStorage.setItem(this.KEYS.TARGET_FRAMEWORK, f);
    },
    
    getConversionResult() {
        try {
            return JSON.parse(localStorage.getItem(this.KEYS.CONVERSION_RESULT) || "null");
        } catch(e) {
            return null;
        }
    },
    
    setConversionResult(r) {
        localStorage.setItem(this.KEYS.CONVERSION_RESULT, JSON.stringify(r || null));
    },
    
    clear() {
        Object.values(this.KEYS).forEach(k => localStorage.removeItem(k));
    }
};

// Export to window
window.State = State;

