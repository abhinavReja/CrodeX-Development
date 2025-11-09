from pathlib import Path
from typing import Dict, List
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class FileCounter:
    """
    Counts and categorizes files in a project
    """
    
    # File categories
    CATEGORIES = {
        'code': ['.py', '.js', '.jsx', '.ts', '.tsx', '.php', '.java', 
                '.c', '.cpp', '.cs', '.rb', '.go', '.rs', '.kt', '.swift'],
        'frontend': ['.html', '.htm', '.css', '.scss', '.sass', '.less', 
                    '.vue', '.svelte'],
        'config': ['.json', '.yaml', '.yml', '.toml', '.ini', '.env', 
                  '.xml', '.conf'],
        'documentation': ['.md', '.txt', '.rst', '.adoc'],
        'data': ['.sql', '.csv', '.xlsx', '.db', '.sqlite'],
        'image': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp'],
        'font': ['.ttf', '.woff', '.woff2', '.eot', '.otf'],
        'archive': ['.zip', '.tar', '.gz', '.rar', '.7z']
    }
    
    def count_files(self, directory: str) -> Dict:
        """
        Count and categorize all files in directory
        
        Args:
            directory: Directory to analyze
            
        Returns:
            Dictionary with file statistics
        """
        try:
            directory_path = Path(directory)
            
            stats = {
                'total_files': 0,
                'total_size': 0,
                'by_extension': defaultdict(lambda: {'count': 0, 'size': 0}),
                'by_category': defaultdict(lambda: {'count': 0, 'size': 0}),
                'largest_files': [],
                'file_list': []
            }
            
            # Collect all files
            all_files = []
            
            for file_path in directory_path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                # Skip hidden and system files
                if any(part.startswith('.') for part in file_path.parts):
                    continue
                
                try:
                    size = file_path.stat().st_size
                    ext = file_path.suffix.lower()
                    
                    # Update stats
                    stats['total_files'] += 1
                    stats['total_size'] += size
                    
                    # By extension
                    stats['by_extension'][ext]['count'] += 1
                    stats['by_extension'][ext]['size'] += size
                    
                    # By category
                    category = self._get_category(ext)
                    stats['by_category'][category]['count'] += 1
                    stats['by_category'][category]['size'] += size
                    
                    # Store file info
                    file_info = {
                        'path': str(file_path.relative_to(directory_path)),
                        'size': size,
                        'extension': ext,
                        'category': category
                    }
                    
                    all_files.append(file_info)
                    
                except (OSError, PermissionError):
                    continue
            
            # Get largest files
            all_files.sort(key=lambda x: x['size'], reverse=True)
            stats['largest_files'] = all_files[:10]
            stats['file_list'] = [f['path'] for f in all_files]
            
            # Convert defaultdicts to regular dicts
            stats['by_extension'] = dict(stats['by_extension'])
            stats['by_category'] = dict(stats['by_category'])
            
            logger.info(f"Counted {stats['total_files']} files in {directory}")
            return stats
            
        except Exception as e:
            logger.error(f"Error counting files: {str(e)}")
            return {}
    
    def _get_category(self, extension: str) -> str:
        """
        Get category for file extension
        
        Args:
            extension: File extension
            
        Returns:
            Category name
        """
        for category, extensions in self.CATEGORIES.items():
            if extension in extensions:
                return category
        
        return 'other'
    
    def count_lines_of_code(self, directory: str) -> Dict:
        """
        Count lines of code in project
        
        Args:
            directory: Directory to analyze
            
        Returns:
            Dictionary with LOC statistics
        """
        try:
            directory_path = Path(directory)
            
            stats = {
                'total_lines': 0,
                'code_lines': 0,
                'comment_lines': 0,
                'blank_lines': 0,
                'by_language': defaultdict(lambda: {
                    'files': 0,
                    'lines': 0,
                    'code': 0,
                    'comments': 0,
                    'blanks': 0
                })
            }
            
            code_extensions = [ext for ext in self.CATEGORIES['code']]
            
            for file_path in directory_path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                ext = file_path.suffix.lower()
                if ext not in code_extensions:
                    continue
                
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    lines = content.splitlines()
                    
                    file_stats = self._analyze_code_lines(lines, ext)
                    
                    # Update totals
                    stats['total_lines'] += file_stats['total']
                    stats['code_lines'] += file_stats['code']
                    stats['comment_lines'] += file_stats['comments']
                    stats['blank_lines'] += file_stats['blanks']
                    
                    # Update by language
                    language = self._get_language(ext)
                    stats['by_language'][language]['files'] += 1
                    stats['by_language'][language]['lines'] += file_stats['total']
                    stats['by_language'][language]['code'] += file_stats['code']
                    stats['by_language'][language]['comments'] += file_stats['comments']
                    stats['by_language'][language]['blanks'] += file_stats['blanks']
                    
                except (UnicodeDecodeError, PermissionError):
                    continue
            
            stats['by_language'] = dict(stats['by_language'])
            
            return stats
            
        except Exception as e:
            logger.error(f"Error counting lines: {str(e)}")
            return {}
    
    def _analyze_code_lines(self, lines: List[str], extension: str) -> Dict:
        """
        Analyze code lines
        
        Args:
            lines: List of code lines
            extension: File extension
            
        Returns:
            Dictionary with line counts
        """
        stats = {
            'total': len(lines),
            'code': 0,
            'comments': 0,
            'blanks': 0
        }
        
        in_block_comment = False
        
        for line in lines:
            stripped = line.strip()
            
            # Blank line
            if not stripped:
                stats['blanks'] += 1
                continue
            
            # Block comments (simplified detection)
            if extension in ['.py']:
                if '"""' in stripped or "'''" in stripped:
                    in_block_comment = not in_block_comment
                    stats['comments'] += 1
                    continue
            elif extension in ['.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.cs']:
                if '/*' in stripped:
                    in_block_comment = True
                if '*/' in stripped:
                    in_block_comment = False
                    stats['comments'] += 1
                    continue
            
            if in_block_comment:
                stats['comments'] += 1
                continue
            
            # Single-line comments
            if extension in ['.py']:
                if stripped.startswith('#'):
                    stats['comments'] += 1
                    continue
            elif extension in ['.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.cs']:
                if stripped.startswith('//'):
                    stats['comments'] += 1
                    continue
            elif extension in ['.php']:
                if stripped.startswith('#') or stripped.startswith('//'):
                    stats['comments'] += 1
                    continue
            
            # Code line
            stats['code'] += 1
        
        return stats
    
    def _get_language(self, extension: str) -> str:
        """Map extension to language name"""
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.php': 'PHP',
            '.java': 'Java',
            '.c': 'C',
            '.cpp': 'C++',
            '.cs': 'C#',
            '.rb': 'Ruby',
            '.go': 'Go',
            '.rs': 'Rust',
            '.kt': 'Kotlin',
            '.swift': 'Swift'
        }
        
        return language_map.get(extension, 'Unknown')

