// Analysis page JavaScript - Load and display analysis results

/**
 * Load analysis data from API
 */
async function loadAnalysis(fileId) {
    try {
        showLoading('Loading analysis results...');
        
        const response = await fetch(`/api/file-analysis/${fileId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.analysis) {
            // Store analysis in state
            State.setFileId(fileId);
            State.setAnalysis(data.analysis);
            
            // Display analysis
            displayAnalysis(data.analysis);
            animateResults();
        } else {
            throw new Error('No analysis data received');
        }
    } catch (error) {
        console.error('Error loading analysis:', error);
        showToast('Failed to load analysis results', 'error');
        
        // Try to load from state as fallback
        const storedAnalysis = State.getAnalysis();
        if (storedAnalysis) {
            displayAnalysis(storedAnalysis);
            animateResults();
        }
    } finally {
        hideLoading();
    }
}

/**
 * Display analysis data on the page
 */
function displayAnalysis(analysis) {
    displayFramework(analysis.framework, analysis.confidence);
    displayStructure(analysis.structure || {});
    displayDependencies(analysis.dependencies || []);
    displayDatabaseInfo(analysis.database || analysis.db || {});
    displayAINotes(analysis.notes || "");
}

/**
 * Display framework information
 */
function displayFramework(framework, confidence) {
    const detectedFramework = document.getElementById('detected-framework');
    const frameworkIcon = document.getElementById('framework-icon');
    const confidenceFill = document.getElementById('confidence-fill');
    const confidencePercent = document.getElementById('confidence-percent');

    if (detectedFramework) {
        detectedFramework.textContent = framework || 'Unknown';
    }
    
    const iconClass = getFrameworkIconClass(framework);
    if (frameworkIcon) {
        frameworkIcon.innerHTML = `<i class="${iconClass}"></i>`;
    }

    const conf = Math.max(0, Math.min(100, Math.round(Number(confidence) || 0)));
    setTimeout(() => {
        if (confidenceFill) {
            confidenceFill.style.width = conf + '%';
        }
        if (confidencePercent) {
            confidencePercent.textContent = conf + '%';
        }
    }, 300);
}

/**
 * Get framework icon class
 */
function getFrameworkIconClass(framework) {
    const map = {
        'Laravel': 'fab fa-laravel',
        'Django': 'fab fa-python',
        'Flask': 'fab fa-python',
        'Express.js': 'fab fa-node-js',
        'Spring Boot': 'fab fa-java',
        'ASP.NET Core': 'fab fa-microsoft',
        'Symfony': 'fab fa-symfony',
        'CodeIgniter': 'fab fa-php'
    };
    
    // Try to match by startsWith to handle "Laravel 10.x"
    if (framework) {
        const key = Object.keys(map).find(k => 
            framework.toLowerCase().startsWith(k.toLowerCase())
        );
        if (key) {
            return map[key];
        }
    }
    
    return 'fas fa-code';
}

/**
 * Display project structure
 */
function displayStructure(structure) {
    let controllers = 0, models = 0, views = 0, routes = 0;
    
    if (structure && structure.components) {
        controllers = (structure.components.controllers || []).length;
        models = (structure.components.models || []).length;
        views = (structure.components.views || []).length;
        routes = (structure.components.routes || []).length;
    } else if (structure) {
        controllers = structure.controllers || 0;
        models = structure.models || 0;
        views = structure.views || 0;
        routes = structure.routes || 0;
    }
    
    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = `${val} files`;
    };
    
    set('controllers-count', controllers);
    set('models-count', models);
    set('views-count', views);
    set('routes-count', routes);
}

/**
 * Display dependencies
 */
function displayDependencies(dependencies) {
    const container = document.getElementById('dependencies-list');
    if (!container) return;
    
    if (!dependencies || !dependencies.length) {
        container.innerHTML = '<p class="text-gray-500">No dependencies detected</p>';
        return;
    }
    
    const items = dependencies.map(dep => {
        if (typeof dep === 'string') {
            return `<div class="dependency-tag"><i class="fas fa-cube"></i> ${dep}</div>`;
        }
        const label = [dep.name, dep.version].filter(Boolean).join('@');
        return `<div class="dependency-tag"><i class="fas fa-cube"></i> ${label}</div>`;
    }).join('');
    
    container.innerHTML = items;
}

/**
 * Display database information
 */
function displayDatabaseInfo(db) {
    const type = db.type || 'Not detected';
    const migrationsFound = !!(db.migrations_found || db.migrations);
    const tables = db.tables || [];

    const setHTML = (id, html) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = html;
    };
    
    const setText = (id, text) => {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    };

    setText('db-type', type);
    setHTML('migrations-found', migrationsFound
        ? '<i class="fas fa-check-circle text-success"></i> Yes'
        : '<i class="fas fa-times-circle text-error"></i> No');
    setText('tables-list', tables.length ? tables.join(', ') : 'None detected');
}

/**
 * Display AI notes
 */
function displayAINotes(notes) {
    const container = document.getElementById('ai-notes');
    if (!container) return;
    
    if (!notes) {
        container.innerHTML = '<p>No additional notes</p>';
        return;
    }
    
    container.innerHTML = `<p>${notes}</p>`;
}

/**
 * Animate result cards
 */
function animateResults() {
    const cards = document.querySelectorAll('.result-card');
    cards.forEach((card, i) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 80 * i);
    });
}

// Export functions to window
window.loadAnalysis = loadAnalysis;
window.displayAnalysis = displayAnalysis;

