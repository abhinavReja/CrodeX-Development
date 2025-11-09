import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FrameworkAnalyzer:
    """
    Analyzes project structure to detect framework
    """
    
    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        'Laravel': {
            'files': ['artisan', 'composer.json'],
            'directories': ['app/Http', 'app/Models', 'routes', 'resources/views'],
            'content_patterns': {
                'composer.json': ['laravel/framework']
            }
        },
        'Django': {
            'files': ['manage.py', 'requirements.txt'],
            'directories': ['*/settings.py', '*/urls.py', '*/wsgi.py'],
            'content_patterns': {
                'requirements.txt': ['django'],
                'manage.py': ['django']
            }
        },
        'Flask': {
            'files': ['app.py', 'requirements.txt'],
            'content_patterns': {
                'requirements.txt': ['flask'],
                'app.py': ['Flask']
            }
        },
        'Express.js': {
            'files': ['package.json'],
            'directories': ['routes', 'views'],
            'content_patterns': {
                'package.json': ['express']
            }
        },
        'Spring Boot': {
            'files': ['pom.xml', 'build.gradle'],
            'directories': ['src/main/java'],
            'content_patterns': {
                'pom.xml': ['spring-boot'],
                'build.gradle': ['spring-boot']
            }
        },
        'ASP.NET Core': {
            'files': ['*.csproj', 'Startup.cs', 'Program.cs'],
            'directories': ['Controllers', 'Models', 'Views'],
            'content_patterns': {
                '*.csproj': ['Microsoft.AspNetCore']
            }
        },
        'Symfony': {
            'files': ['composer.json', 'symfony.lock'],
            'directories': ['src', 'config', 'var'],
            'content_patterns': {
                'composer.json': ['symfony/framework-bundle']
            }
        },
        'CodeIgniter': {
            'files': ['index.php'],
            'directories': ['application', 'system'],
            'content_patterns': {
                'index.php': ['CodeIgniter']
            }
        }
    }
    
    def __init__(self):
        self.detected_framework = None
        self.confidence = 0
    
    def analyze(self, directory: str) -> Dict:
        """
        Analyze directory to detect framework
        
        Args:
            directory: Project directory path
            
        Returns:
            Dictionary with analysis results
        """
        try:
            directory_path = Path(directory)
            
            # Score each framework
            scores = {}
            for framework, patterns in self.FRAMEWORK_PATTERNS.items():
                score = self._calculate_framework_score(directory_path, patterns)
                scores[framework] = score
            
            # Get best match
            if scores:
                best_framework = max(scores, key=scores.get)
                confidence = scores[best_framework]
            else:
                best_framework = 'Unknown'
                confidence = 0
            
            # Analyze structure
            structure = self._analyze_structure(directory_path, best_framework)
            
            # Get dependencies
            dependencies = self._extract_dependencies(directory_path, best_framework)
            
            # Database info
            database_info = self._analyze_database(directory_path, best_framework)
            
            # Generate notes
            notes = self._generate_notes(directory_path, best_framework, confidence)
            
            result = {
                'framework': best_framework,
                'confidence': min(confidence, 100),
                'structure': structure,
                'dependencies': dependencies,
                'database': database_info,
                'notes': notes,
                'all_scores': scores
            }
            
            logger.info(f"Analysis complete: {best_framework} (confidence: {confidence}%)")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing project: {str(e)}")
            raise
    
    def analyze_structure(self, files: Dict[str, str]) -> Dict:
        """
        Analyze project structure from a dictionary of files
        (for use with converter.py - accepts files dict instead of directory)
        
        Args:
            files: Dictionary mapping file paths to file contents
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Create a temporary analysis from files dictionary
            file_paths = list(files.keys())
            
            # Detect framework based on file names and content
            scores = {}
            for framework, patterns in self.FRAMEWORK_PATTERNS.items():
                score = self._calculate_framework_score_from_files(file_paths, files, patterns)
                scores[framework] = score
            
            # Get best match
            if scores:
                best_framework = max(scores, key=scores.get)
                confidence = scores[best_framework]
            else:
                best_framework = 'Unknown'
                confidence = 0
            
            # Analyze structure from files
            structure = self._analyze_structure_from_files(file_paths, files, best_framework)
            
            # Get dependencies from files
            dependencies = self._extract_dependencies_from_files(files, best_framework)
            
            # Simple database info (can't analyze deeply from files dict alone)
            database_info = {
                'type': 'Unknown',
                'migrations_found': any('migration' in path.lower() for path in file_paths),
                'tables': []
            }
            
            # Generate notes with more detail
            notes_parts = [f"Analyzed {len(files)} files. Framework: {best_framework} (confidence: {confidence}%)"]
            if dependencies:
                notes_parts.append(f"Found {len(dependencies)} dependencies")
            if structure.get('components', {}).get('controllers'):
                notes_parts.append(f"Detected {len(structure['components']['controllers'])} controllers")
            if structure.get('components', {}).get('models'):
                notes_parts.append(f"Detected {len(structure['components']['models'])} models")
            
            notes = ". ".join(notes_parts)
            
            result = {
                'primary_framework': best_framework,  # Keep for backward compatibility
                'framework': best_framework,  # Add framework key for consistency
                'confidence': min(confidence, 100),
                'structure': structure,
                'dependencies': dependencies,
                'database': database_info,
                'notes': notes,
                'file_stats': {
                    'total_files': len(files),
                    'total_size': sum(len(content) for content in files.values())
                },
                'all_scores': scores,
                'file_count': len(files)
            }
            
            logger.info(f"Structure analysis complete: {best_framework} (confidence: {confidence}%)")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing structure: {str(e)}")
            raise
    
    def _calculate_framework_score_from_files(self, file_paths: List[str], 
                                             files: Dict[str, str],
                                             patterns: Dict) -> int:
        """Calculate framework score from files dictionary"""
        score = 0
        max_score = 0
        
        # Check files (30 points)
        if 'files' in patterns:
            max_score += 30
            file_score = 0
            for file_pattern in patterns['files']:
                # Check if any file path matches the pattern
                for file_path in file_paths:
                    filename = Path(file_path).name
                    if self._match_pattern(filename, file_pattern):
                        file_score += 30 / len(patterns['files'])
                        break
            score += file_score
        
        # Check directories (30 points) - check file paths
        if 'directories' in patterns:
            max_score += 30
            dir_score = 0
            for dir_pattern in patterns['directories']:
                for file_path in file_paths:
                    if self._match_directory_pattern(file_path, dir_pattern):
                        dir_score += 30 / len(patterns['directories'])
                        break
            score += dir_score
        
        # Check content patterns (40 points)
        if 'content_patterns' in patterns:
            max_score += 40
            content_score = 0
            for file_pattern, patterns_list in patterns['content_patterns'].items():
                for file_path, content in files.items():
                    filename = Path(file_path).name
                    if self._match_pattern(filename, file_pattern):
                        if content:
                            for pattern in patterns_list:
                                if pattern in content:
                                    content_score += 40 / (len(patterns['content_patterns']) * len(patterns_list))
                                    break
            score += content_score
        
        # Normalize to 100
        if max_score > 0:
            score = (score / max_score) * 100
        
        return int(score)
    
    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches pattern"""
        if '*' in pattern:
            import fnmatch
            return fnmatch.fnmatch(filename, pattern)
        return filename == pattern
    
    def _match_directory_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches directory pattern"""
        if '*' in pattern:
            parts = pattern.split('/')
            path_parts = file_path.split('/')
            # Simple pattern matching
            for part in parts:
                if '*' in part:
                    continue
                if part not in path_parts:
                    return False
            return True
        return pattern in file_path
    
    def _analyze_structure_from_files(self, file_paths: List[str], 
                                     files: Dict[str, str],
                                     framework: str) -> Dict:
        """Analyze structure from files dictionary"""
        structure = {
            'components': {
                'controllers': [],
                'models': [],
                'views': [],
                'routes': []
            },
            'total_files': len(file_paths),
            'total_size': sum(len(content) for content in files.values())
        }
        
        # Framework-specific component detection
        for file_path in file_paths:
            path_lower = file_path.lower()
            if 'controller' in path_lower:
                structure['components']['controllers'].append(file_path)
            elif 'model' in path_lower:
                structure['components']['models'].append(file_path)
            elif 'view' in path_lower or 'template' in path_lower:
                structure['components']['views'].append(file_path)
            elif 'route' in path_lower or 'url' in path_lower:
                structure['components']['routes'].append(file_path)
        
        return structure
    
    def _extract_dependencies_from_files(self, files: Dict[str, str],
                                        framework: str) -> List[str]:
        """Extract dependencies from files dictionary"""
        dependencies = []
        
        # Check for dependency files
        for file_path, content in files.items():
            filename = Path(file_path).name
            if filename == 'composer.json':
                deps = self._parse_composer_json_content(content)
                dependencies.extend(deps)
            elif filename == 'package.json':
                deps = self._parse_package_json_content(content)
                dependencies.extend(deps)
            elif filename == 'requirements.txt':
                deps = self._parse_requirements_txt_content(content)
                dependencies.extend(deps)
            elif filename.endswith('.csproj'):
                deps = self._parse_csproj_content(content)
                dependencies.extend(deps)
        
        return list(set(dependencies))  # Remove duplicates
    
    def _parse_composer_json_content(self, content: str) -> List[str]:
        """Parse composer.json content"""
        try:
            data = json.loads(content)
            if 'require' in data:
                return list(data['require'].keys())
        except Exception:
            pass
        return []
    
    def _parse_package_json_content(self, content: str) -> List[str]:
        """Parse package.json content"""
        try:
            data = json.loads(content)
            if 'dependencies' in data:
                return list(data['dependencies'].keys())
        except Exception:
            pass
        return []
    
    def _parse_requirements_txt_content(self, content: str) -> List[str]:
        """Parse requirements.txt content"""
        try:
            deps = []
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    dep = line.split('==')[0].split('>=')[0].split('<=')[0]
                    deps.append(dep)
            return deps
        except Exception:
            return []
    
    def _parse_csproj_content(self, content: str) -> List[str]:
        """Parse .csproj content"""
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)
            deps = []
            for package_ref in root.findall('.//PackageReference'):
                include = package_ref.get('Include')
                if include:
                    deps.append(include)
            return deps
        except Exception:
            return []
    
    def _calculate_framework_score(self, directory: Path, 
                                   patterns: Dict) -> int:
        """
        Calculate framework detection score
        
        Args:
            directory: Project directory
            patterns: Framework patterns
            
        Returns:
            Score (0-100)
        """
        score = 0
        max_score = 0
        
        # Check files (30 points)
        if 'files' in patterns:
            max_score += 30
            file_score = 0
            for file_pattern in patterns['files']:
                if self._find_files(directory, file_pattern):
                    file_score += 30 / len(patterns['files'])
            score += file_score
        
        # Check directories (30 points)
        if 'directories' in patterns:
            max_score += 30
            dir_score = 0
            for dir_pattern in patterns['directories']:
                if self._find_directories(directory, dir_pattern):
                    dir_score += 30 / len(patterns['directories'])
            score += dir_score
        
        # Check content patterns (40 points)
        if 'content_patterns' in patterns:
            max_score += 40
            content_score = 0
            for file_pattern, patterns_list in patterns['content_patterns'].items():
                files = self._find_files(directory, file_pattern)
                for file in files:
                    content = self._read_file_safe(file)
                    if content:
                        for pattern in patterns_list:
                            if pattern in content:
                                content_score += 40 / (len(patterns['content_patterns']) * len(patterns_list))
            score += content_score
        
        # Normalize to 100
        if max_score > 0:
            score = (score / max_score) * 100
        
        return int(score)
    
    def _find_files(self, directory: Path, pattern: str) -> List[Path]:
        """Find files matching pattern"""
        try:
            if '*' in pattern:
                return list(directory.rglob(pattern))
            else:
                file_path = directory / pattern
                return [file_path] if file_path.exists() else []
        except Exception:
            return []
    
    def _find_directories(self, directory: Path, pattern: str) -> List[Path]:
        """Find directories matching pattern"""
        try:
            if '*' in pattern:
                # Handle wildcard patterns
                parts = pattern.split('/')
                current = directory
                
                for part in parts:
                    if '*' in part:
                        matches = list(current.glob(part))
                        if matches:
                            return matches
                    else:
                        current = current / part
                        if not current.exists():
                            return []
                
                return [current] if current.exists() else []
            else:
                dir_path = directory / pattern
                return [dir_path] if dir_path.is_dir() else []
        except Exception:
            return []
    
    def _read_file_safe(self, file_path: Path) -> Optional[str]:
        """Safely read file content"""
        try:
            # Skip large files
            if file_path.stat().st_size > 1024 * 1024:  # 1MB
                return None
            
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return None
    
    def _analyze_structure(self, directory: Path, framework: str) -> Dict:
        """Analyze project structure"""
        structure = {
            'components': {
                'controllers': [],
                'models': [],
                'views': [],
                'routes': []
            },
            'total_files': 0,
            'total_size': 0
        }
        
        # Framework-specific paths
        component_paths = {
            'Laravel': {
                'controllers': 'app/Http/Controllers',
                'models': 'app/Models',
                'views': 'resources/views',
                'routes': 'routes'
            },
            'Django': {
                'views': '*/views.py',
                'models': '*/models.py',
                'routes': '*/urls.py'
            },
            'Flask': {
                'routes': '*.py'
            },
            'Express.js': {
                'routes': 'routes',
                'views': 'views'
            }
        }
        
        if framework in component_paths:
            paths = component_paths[framework]
            
            for component, path_pattern in paths.items():
                files = self._find_files(directory, path_pattern)
                dirs = self._find_directories(directory, path_pattern)
                
                all_items = files + dirs
                for item in all_items:
                    if item.is_file():
                        structure['components'][component].append(str(item.name))
                    elif item.is_dir():
                        # Add files in directory
                        for file in item.rglob('*'):
                            if file.is_file():
                                structure['components'][component].append(
                                    str(file.relative_to(directory))
                                )
        
        # Count total files and size
        for file in directory.rglob('*'):
            if file.is_file():
                structure['total_files'] += 1
                try:
                    structure['total_size'] += file.stat().st_size
                except Exception:
                    pass
        
        return structure
    
    def _extract_dependencies(self, directory: Path, 
                            framework: str) -> List[str]:
        """Extract project dependencies"""
        dependencies = []
        
        # Check different dependency files
        dep_files = {
            'composer.json': self._parse_composer_json,
            'package.json': self._parse_package_json,
            'requirements.txt': self._parse_requirements_txt,
            'pom.xml': self._parse_pom_xml,
            '*.csproj': self._parse_csproj
        }
        
        for file_pattern, parser in dep_files.items():
            files = self._find_files(directory, file_pattern)
            for file in files:
                deps = parser(file)
                dependencies.extend(deps)
        
        return list(set(dependencies))  # Remove duplicates
    
    def _parse_composer_json(self, file_path: Path) -> List[str]:
        """Parse composer.json for dependencies"""
        try:
            content = json.loads(file_path.read_text())
            deps = []
            
            if 'require' in content:
                deps.extend(content['require'].keys())
            
            return deps
        except Exception:
            return []
    
    def _parse_package_json(self, file_path: Path) -> List[str]:
        """Parse package.json for dependencies"""
        try:
            content = json.loads(file_path.read_text())
            deps = []
            
            if 'dependencies' in content:
                deps.extend(content['dependencies'].keys())
            
            return deps
        except Exception:
            return []
    
    def _parse_requirements_txt(self, file_path: Path) -> List[str]:
        """Parse requirements.txt for dependencies"""
        try:
            content = file_path.read_text()
            deps = []
            
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name
                    dep = line.split('==')[0].split('>=')[0].split('<=')[0]
                    deps.append(dep)
            
            return deps
        except Exception:
            return []
    
    def _parse_pom_xml(self, file_path: Path) -> List[str]:
        """Parse pom.xml for dependencies"""
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            deps = []
            ns = {'maven': 'http://maven.apache.org/POM/4.0.0'}
            
            for dep in root.findall('.//maven:dependency', ns):
                artifact = dep.find('maven:artifactId', ns)
                if artifact is not None:
                    deps.append(artifact.text)
            
            return deps
        except Exception:
            return []
    
    def _parse_csproj(self, file_path: Path) -> List[str]:
        """Parse .csproj for dependencies"""
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            deps = []
            
            for package_ref in root.findall('.//PackageReference'):
                include = package_ref.get('Include')
                if include:
                    deps.append(include)
            
            return deps
        except Exception:
            return []
    
    def _analyze_database(self, directory: Path, framework: str) -> Dict:
        """Analyze database configuration"""
        db_info = {
            'type': 'Unknown',
            'migrations_found': False,
            'tables': []
        }
        
        # Look for database config files
        config_patterns = {
            'Laravel': ['.env', 'config/database.php'],
            'Django': ['settings.py', '*/settings.py'],
            'Flask': ['config.py', 'app.py'],
            'Express.js': ['.env', 'config.js']
        }
        
        if framework in config_patterns:
            for pattern in config_patterns[framework]:
                files = self._find_files(directory, pattern)
                for file in files:
                    content = self._read_file_safe(file)
                    if content:
                        # Detect database type
                        if 'mysql' in content.lower():
                            db_info['type'] = 'MySQL'
                        elif 'postgres' in content.lower():
                            db_info['type'] = 'PostgreSQL'
                        elif 'sqlite' in content.lower():
                            db_info['type'] = 'SQLite'
                        elif 'mongodb' in content.lower():
                            db_info['type'] = 'MongoDB'
        
        # Check for migrations
        migration_dirs = ['database/migrations', 'migrations', '*/migrations']
        for pattern in migration_dirs:
            dirs = self._find_directories(directory, pattern)
            if dirs:
                db_info['migrations_found'] = True
                
                # Try to extract table names from migrations
                for migration_dir in dirs:
                    for file in migration_dir.glob('*.py'):
                        content = self._read_file_safe(file)
                        if content:
                            # Simple extraction (can be improved)
                            import re
                            tables = re.findall(r'create_table\([\'"](\w+)[\'"]', content)
                            db_info['tables'].extend(tables)
                
                break
        
        db_info['tables'] = list(set(db_info['tables']))[:10]  # Limit to 10
        
        return db_info
    
    def _generate_notes(self, directory: Path, framework: str, 
                       confidence: int) -> str:
        """Generate AI-style analysis notes"""
        notes = []
        
        if confidence < 50:
            notes.append("⚠ Low confidence in framework detection. Manual verification recommended.")
        elif confidence < 80:
            notes.append("ℹ Framework detected with moderate confidence. Some features may need manual review.")
        else:
            notes.append("✅ Framework detected with high confidence.")
        
        # Check for common patterns
        if self._find_files(directory, 'docker-compose.yml'):
            notes.append("🐳 Docker configuration detected.")
        
        if self._find_directories(directory, 'tests'):
            notes.append("🧪 Test suite detected.")
        
        if self._find_files(directory, '.env'):
            notes.append("⚙ Environment configuration found.")
        
        if self._find_directories(directory, '.git'):
            notes.append("📚 Git repository detected.")
        
        return " ".join(notes)
