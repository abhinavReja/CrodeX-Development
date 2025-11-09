import os
import re
from typing import Dict, List, Tuple
from collections import defaultdict

class FrameworkAnalyzer:
    """
    Analyzes project structure to detect framework
    Works in conjunction with Claude for confirmation
    """
    
    FRAMEWORK_SIGNATURES = {
        'laravel': {
            'files': ['artisan', 'composer.json'],
            'dirs': ['app/Http/Controllers', 'resources/views', 'routes'],
            'patterns': [r'namespace App\\', r'use Illuminate\\']
        },
        'codeigniter': {
            'files': ['index.php'],
            'dirs': ['application/controllers', 'application/models', 'system'],
            'patterns': [r'class \w+ extends CI_Controller', r'\$this->load->']
        },
        'symfony': {
            'files': ['composer.json', 'symfony.lock'],
            'dirs': ['src/Controller', 'config', 'templates'],
            'patterns': [r'namespace App\\Controller', r'use Symfony\\']
        },
        'django': {
            'files': ['manage.py', 'requirements.txt'],
            'dirs': ['templates', 'static'],
            'patterns': [r'from django\.', r'INSTALLED_APPS']
        },
        'flask': {
            'files': ['app.py', 'wsgi.py', 'requirements.txt'],
            'patterns': [r'from flask import', r'@app\.route']
        },
        'express': {
            'files': ['package.json', 'server.js', 'app.js'],
            'patterns': [r'const express = require', r'app\.use\(']
        }
    }
    
    def __init__(self):
        self.file_tree = defaultdict(list)
        self.file_contents = {}
    
    def analyze_structure(self, files: Dict[str, str]) -> Dict:
        """
        Initial rapid analysis before Claude
        
        Returns:
            Dict with preliminary detection results
        """
        self.file_contents = files
        self._build_file_tree(files)
        
        # Detect framework
        detected_frameworks = []
        
        for framework, signature in self.FRAMEWORK_SIGNATURES.items():
            score = self._calculate_framework_score(framework, signature)
            if score > 0:
                detected_frameworks.append({
                    'framework': framework,
                    'score': score,
                    'confidence': min(score * 10, 100)
                })
        
        # Sort by score
        detected_frameworks.sort(key=lambda x: x['score'], reverse=True)
        
        # Build structure analysis
        structure = self._analyze_project_structure()
        
        return {
            'detected_frameworks': detected_frameworks,
            'primary_framework': detected_frameworks[0] if detected_frameworks else None,
            'structure': structure,
            'file_stats': {
                'total_files': len(files),
                'code_files': len([f for f in files if self._is_code_file(f)]),
                'total_lines': sum(len(c.splitlines()) for c in files.values())
            }
        }
    
    def _build_file_tree(self, files: Dict[str, str]):
        """Build directory tree structure"""
        for file_path in files.keys():
            parts = file_path.split('/')
            for i in range(len(parts)):
                dir_path = '/'.join(parts[:i+1])
                if i < len(parts) - 1:  # It's a directory
                    self.file_tree['/'.join(parts[:i])].append(parts[i])
    
    def _calculate_framework_score(self, framework: str, signature: Dict) -> int:
        """Calculate match score for framework"""
        score = 0
        
        # Check required files
        for required_file in signature.get('files', []):
            if any(required_file in path for path in self.file_contents.keys()):
                score += 3
        
        # Check required directories
        for required_dir in signature.get('dirs', []):
            if any(required_dir in path for path in self.file_contents.keys()):
                score += 2
        
        # Check code patterns
        for pattern in signature.get('patterns', []):
            regex = re.compile(pattern)
            for content in self.file_contents.values():
                if regex.search(content):
                    score += 1
                    break
        
        return score
    
    def _analyze_project_structure(self) -> Dict:
        """Analyze project organization"""
        structure = {
            'type': 'unknown',
            'architecture': [],
            'components': {
                'controllers': [],
                'models': [],
                'views': [],
                'routes': [],
                'config': [],
                'migrations': [],
                'tests': []
            },
            'entry_points': []
        }
        
        # Detect architecture type
        if any('controllers' in path.lower() for path in self.file_contents.keys()):
            structure['architecture'].append('MVC')
        
        if any('api' in path.lower() for path in self.file_contents.keys()):
            structure['architecture'].append('API')
        
        # Categorize files
        for file_path in self.file_contents.keys():
            lower_path = file_path.lower()
            
            if 'controller' in lower_path:
                structure['components']['controllers'].append(file_path)
            elif 'model' in lower_path:
                structure['components']['models'].append(file_path)
            elif 'view' in lower_path or 'template' in lower_path:
                structure['components']['views'].append(file_path)
            elif 'route' in lower_path:
                structure['components']['routes'].append(file_path)
            elif 'config' in lower_path:
                structure['components']['config'].append(file_path)
            elif 'migration' in lower_path:
                structure['components']['migrations'].append(file_path)
            elif 'test' in lower_path:
                structure['components']['tests'].append(file_path)
            
            # Detect entry points
            if file_path.endswith(('index.php', 'app.py', 'server.js', 'main.go')):
                structure['entry_points'].append(file_path)
        
        return structure
    
    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file"""
        code_extensions = [
            '.php', '.py', '.js', '.ts', '.jsx', '.tsx',
            '.java', '.rb', '.go', '.cs', '.rs', '.cpp',
            '.c', '.h', '.hpp', '.swift', '.kt'
        ]
        return any(file_path.endswith(ext) for ext in code_extensions)
    
    def get_file_dependencies(self, file_path: str) -> List[str]:
        """Extract dependencies/imports from file"""
        content = self.file_contents.get(file_path, '')
        dependencies = []
        
        # PHP imports
        php_imports = re.findall(r'use\s+([\w\\]+);', content)
        dependencies.extend(php_imports)
        
        # Python imports
        python_imports = re.findall(r'(?:from|import)\s+([\w.]+)', content)
        dependencies.extend(python_imports)
        
        # JavaScript imports
        js_imports = re.findall(r'(?:import|require)\s*\([\'"](.+?)[\'"]\)', content)
        dependencies.extend(js_imports)
        
        return list(set(dependencies))