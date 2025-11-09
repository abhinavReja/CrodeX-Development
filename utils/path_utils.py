import os
import re
from pathlib import Path
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class PathUtils:
    """
    Utility functions for path operations
    """
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalize path to use forward slashes
        
        Args:
            path: Path string
            
        Returns:
            Normalized path
        """
        return str(Path(path).as_posix())
    
    @staticmethod
    def get_relative_path(path: str, base_path: str) -> str:
        """
        Get relative path from base path
        
        Args:
            path: Full path
            base_path: Base path
            
        Returns:
            Relative path
        """
        try:
            return str(Path(path).relative_to(base_path))
        except ValueError:
            return path
    
    @staticmethod
    def is_subpath(path: str, parent: str) -> bool:
        """
        Check if path is a subpath of parent
        
        Args:
            path: Path to check
            parent: Parent path
            
        Returns:
            True if path is under parent
        """
        try:
            Path(path).resolve().relative_to(Path(parent).resolve())
            return True
        except ValueError:
            return False
    
    @staticmethod
    def safe_join(*paths) -> Path:
        """
        Safely join paths (prevents path traversal)
        
        Args:
            *paths: Path components
            
        Returns:
            Joined path
            
        Raises:
            ValueError: If path traversal detected
        """
        base = Path(paths[0]).resolve()
        result = base
        
        for path_part in paths[1:]:
            # Remove any absolute or parent references
            cleaned = str(path_part).lstrip('/\\').replace('..', '')
            result = result / cleaned
        
        # Verify result is still under base
        try:
            result.resolve().relative_to(base)
            return result
        except ValueError:
            raise ValueError("Path traversal attempt detected")
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to remove dangerous characters
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace dangerous characters
        sanitized = re.sub(r'[^\w\s\-\.]', '_', filename)
        
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove leading/trailing underscores and dots
        sanitized = sanitized.strip('_.')
        
        return sanitized
    
    @staticmethod
    def get_file_extension(path: str) -> str:
        """
        Get file extension (including dot)
        
        Args:
            path: File path
            
        Returns:
            Extension string
        """
        return Path(path).suffix.lower()
    
    @staticmethod
    def change_extension(path: str, new_extension: str) -> str:
        """
        Change file extension
        
        Args:
            path: Original path
            new_extension: New extension (with or without dot)
            
        Returns:
            Path with new extension
        """
        p = Path(path)
        
        if not new_extension.startswith('.'):
            new_extension = '.' + new_extension
        
        return str(p.with_suffix(new_extension))
    
    @staticmethod
    def get_directory_name(path: str) -> str:
        """
        Get directory name from path
        
        Args:
            path: Path string
            
        Returns:
            Directory name
        """
        return Path(path).parent.name
    
    @staticmethod
    def ensure_directory(path: str):
        """
        Ensure directory exists, create if not
        
        Args:
            path: Directory path
        """
        Path(path).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def get_common_prefix(paths: List[str]) -> str:
        """
        Get common prefix of multiple paths
        
        Args:
            paths: List of paths
            
        Returns:
            Common prefix path
        """
        if not paths:
            return ""
        
        paths = [Path(p).parts for p in paths]
        common = []
        
        for parts in zip(*paths):
            if len(set(parts)) == 1:
                common.append(parts[0])
            else:
                break
        
        return str(Path(*common)) if common else ""
    
    @staticmethod
    def split_path(path: str) -> List[str]:
        """
        Split path into components
        
        Args:
            path: Path string
            
        Returns:
            List of path components
        """
        return list(Path(path).parts)
    
    @staticmethod
    def is_hidden(path: str) -> bool:
        """
        Check if file/directory is hidden
        
        Args:
            path: Path to check
            
        Returns:
            True if hidden
        """
        name = Path(path).name
        
        # Unix-style hidden files
        if name.startswith('.'):
            return True
        
        # Windows hidden files
        if os.name == 'nt':
            try:
                import ctypes
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
                return bool(attrs & 2)  # FILE_ATTRIBUTE_HIDDEN
            except:
                pass
        
        return False
    
    @staticmethod
    def find_root_directory(path: str, indicators: List[str]) -> Optional[str]:
        """
        Find project root directory by looking for indicator files
        
        Args:
            path: Starting path
            indicators: List of indicator files (e.g., ['package.json', '.git'])
            
        Returns:
            Root directory path or None
        """
        current = Path(path).resolve()
        
        while current != current.parent:
            for indicator in indicators:
                if (current / indicator).exists():
                    return str(current)
            
            current = current.parent
        
        return None
    
    @staticmethod
    def get_file_hierarchy(directory: str, max_depth: int = 3) -> Dict:
        """
        Get file hierarchy as nested dictionary
        
        Args:
            directory: Root directory
            max_depth: Maximum depth
            
        Returns:
            Nested dictionary
        """
        def build_tree(path: Path, depth: int = 0):
            if depth >= max_depth:
                return None
            
            if path.is_file():
                return {
                    'type': 'file',
                    'size': path.stat().st_size
                }
            
            children = {}
            try:
                for item in sorted(path.iterdir()):
                    children[item.name] = build_tree(item, depth + 1)
            except PermissionError:
                pass
            
            return {
                'type': 'directory',
                'children': children
            }
        
        return build_tree(Path(directory))

