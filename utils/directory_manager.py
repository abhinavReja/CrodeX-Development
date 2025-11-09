import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DirectoryManager:
    """
    Manages directory operations
    """
    
    def get_structure(self, directory: str, max_depth: int = 3) -> Dict:
        """
        Get directory structure as nested dictionary
        
        Args:
            directory: Root directory
            max_depth: Maximum depth to traverse
            
        Returns:
            Nested dictionary representing structure
        """
        try:
            def build_tree(path: Path, current_depth: int = 0) -> Dict:
                if current_depth >= max_depth:
                    return {'type': 'max_depth'}
                
                if path.is_file():
                    return {
                        'type': 'file',
                        'size': path.stat().st_size,
                        'extension': path.suffix
                    }
                
                children = {}
                try:
                    for item in path.iterdir():
                        children[item.name] = build_tree(item, current_depth + 1)
                except PermissionError:
                    return {'type': 'permission_denied'}
                
                return {
                    'type': 'directory',
                    'children': children
                }
            
            root_path = Path(directory)
            return build_tree(root_path)
            
        except Exception as e:
            logger.error(f"Error getting directory structure: {str(e)}")
            return {}
    
    def get_directory_size(self, directory: str) -> int:
        """
        Calculate total size of directory
        
        Args:
            directory: Directory path
            
        Returns:
            Total size in bytes
        """
        try:
            total_size = 0
            
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = Path(dirpath) / filename
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, FileNotFoundError):
                        continue
            
            return total_size
            
        except Exception as e:
            logger.error(f"Error calculating directory size: {str(e)}")
            return 0
    
    def list_files_by_extension(self, directory: str, 
                                extension: str) -> List[Path]:
        """
        List all files with given extension
        
        Args:
            directory: Directory to search
            extension: File extension (e.g., '.py')
            
        Returns:
            List of file paths
        """
        try:
            directory_path = Path(directory)
            return list(directory_path.rglob(f'*{extension}'))
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []
    
    def create_directory_tree(self, base_path: str, 
                             structure: Dict[str, any]):
        """
        Create directory structure from dictionary
        
        Args:
            base_path: Base directory path
            structure: Dictionary representing directory structure
        """
        try:
            base = Path(base_path)
            base.mkdir(parents=True, exist_ok=True)
            
            for name, content in structure.items():
                path = base / name
                
                if isinstance(content, dict):
                    # It's a directory
                    self.create_directory_tree(str(path), content)
                else:
                    # It's a file
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if content:
                        path.write_text(str(content))
                    else:
                        path.touch()
            
            logger.debug(f"Created directory tree at: {base_path}")
            
        except Exception as e:
            logger.error(f"Error creating directory tree: {str(e)}")
            raise
    
    def copy_directory(self, source: str, destination: str, 
                      ignore_patterns: Optional[List[str]] = None):
        """
        Copy directory with optional ignore patterns
        
        Args:
            source: Source directory
            destination: Destination directory
            ignore_patterns: List of patterns to ignore
        """
        try:
            if ignore_patterns:
                ignore = shutil.ignore_patterns(*ignore_patterns)
            else:
                ignore = None
            
            shutil.copytree(source, destination, ignore=ignore)
            
            logger.info(f"Copied directory: {source} -> {destination}")
            
        except Exception as e:
            logger.error(f"Error copying directory: {str(e)}")
            raise
    
    def get_file_statistics(self, directory: str) -> Dict:
        """
        Get statistics about files in directory
        
        Args:
            directory: Directory to analyze
            
        Returns:
            Dictionary with statistics
        """
        try:
            stats = {
                'total_files': 0,
                'total_size': 0,
                'by_extension': {},
                'by_type': {
                    'code': 0,
                    'config': 0,
                    'documentation': 0,
                    'other': 0
                }
            }
            
            code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.php', 
                              '.java', '.c', '.cpp', '.cs', '.rb', '.go'}
            config_extensions = {'.json', '.yaml', '.yml', '.toml', '.ini', 
                               '.env', '.config'}
            doc_extensions = {'.md', '.txt', '.rst', '.pdf', '.doc', '.docx'}
            
            for dirpath, _, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = Path(dirpath) / filename
                    
                    try:
                        size = file_path.stat().st_size
                        ext = file_path.suffix.lower()
                        
                        stats['total_files'] += 1
                        stats['total_size'] += size
                        
                        # Count by extension
                        if ext not in stats['by_extension']:
                            stats['by_extension'][ext] = {'count': 0, 'size': 0}
                        stats['by_extension'][ext]['count'] += 1
                        stats['by_extension'][ext]['size'] += size
                        
                        # Categorize
                        if ext in code_extensions:
                            stats['by_type']['code'] += 1
                        elif ext in config_extensions:
                            stats['by_type']['config'] += 1
                        elif ext in doc_extensions:
                            stats['by_type']['documentation'] += 1
                        else:
                            stats['by_type']['other'] += 1
                            
                    except (OSError, FileNotFoundError):
                        continue
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting file statistics: {str(e)}")
            return {}
    
    def find_empty_directories(self, directory: str) -> List[str]:
        """
        Find all empty directories
        
        Args:
            directory: Directory to search
            
        Returns:
            List of empty directory paths
        """
        empty_dirs = []
        
        for dirpath, dirnames, filenames in os.walk(directory, topdown=False):
            if not dirnames and not filenames:
                empty_dirs.append(dirpath)
        
        return empty_dirs
    
    def remove_empty_directories(self, directory: str) -> int:
        """
        Remove all empty directories
        
        Args:
            directory: Directory to clean
            
        Returns:
            Number of directories removed
        """
        empty_dirs = self.find_empty_directories(directory)
        count = 0
        
        for empty_dir in empty_dirs:
            try:
                os.rmdir(empty_dir)
                count += 1
            except OSError:
                continue
        
        logger.info(f"Removed {count} empty directories")
        return count

