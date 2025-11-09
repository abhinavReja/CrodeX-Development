import os
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

from utils.file_extractor import FileExtractor
from utils.file_parser import FileParser
from utils.file_validator import FileValidator
from utils.directory_manager import DirectoryManager
from utils.path_utils import PathUtils

logger = logging.getLogger(__name__)


class FileManager:
    """
    Main file management class
    Handles all file operations for the converter
    """
    
    def __init__(self, base_upload_path: str):
        """
        Initialize FileManager
        
        Args:
            base_upload_path: Base path for file uploads
        """
        self.base_upload_path = Path(base_upload_path)
        self.base_upload_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.extractor = FileExtractor()
        self.parser = FileParser()
        self.validator = FileValidator()
        self.dir_manager = DirectoryManager()
        self.path_utils = PathUtils()
        
        logger.info(f"FileManager initialized with base path: {self.base_upload_path}")
    
    def create_project_directory(self, project_id: str) -> Path:
        """
        Create a unique directory for a project
        
        Args:
            project_id: Unique project identifier
            
        Returns:
            Path to project directory
        """
        project_path = self.base_upload_path / project_id
        project_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created project directory: {project_path}")
        return project_path
    
    def extract_zip(self, zip_path: str, extract_to: str) -> Path:
        """
        Extract ZIP file to specified directory
        
        Args:
            zip_path: Path to ZIP file
            extract_to: Directory to extract to
            
        Returns:
            Path to extracted directory
            
        Raises:
            ValueError: If ZIP file is invalid or corrupted
        """
        try:
            # Validate ZIP file
            if not self.validator.is_valid_zip(zip_path):
                raise ValueError("Invalid or corrupted ZIP file")
            
            # Extract
            extracted_path = self.extractor.extract_zip(zip_path, extract_to)
            
            logger.info(f"Extracted ZIP to: {extracted_path}")
            return extracted_path
            
        except Exception as e:
            logger.error(f"Error extracting ZIP: {str(e)}")
            raise
    
    def load_files(self, directory: str, 
                   extensions: Optional[List[str]] = None,
                   exclude_patterns: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Load all files from directory into memory
        
        Args:
            directory: Directory to load files from
            extensions: List of file extensions to include (e.g., ['.py', '.js'])
            exclude_patterns: List of patterns to exclude (e.g., ['node_modules', '.git'])
            
        Returns:
            Dictionary mapping relative file paths to file contents
        """
        try:
            files_dict = {}
            directory_path = Path(directory)
            
            # Default exclude patterns
            if exclude_patterns is None:
                exclude_patterns = [
                    'node_modules', '.git', '__pycache__', '.venv',
                    'vendor', 'build', 'dist', '.next', '.cache'
                ]
            
            # Walk through directory
            for file_path in directory_path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                # Get relative path
                rel_path = file_path.relative_to(directory_path)
                
                # Check exclusions
                if self._should_exclude(str(rel_path), exclude_patterns):
                    continue
                
                # Check extensions
                if extensions and file_path.suffix not in extensions:
                    continue
                
                # Read file content
                content = self.parser.read_file(file_path)
                if content is not None:
                    files_dict[str(rel_path)] = content
            
            logger.info(f"Loaded {len(files_dict)} files from {directory}")
            return files_dict
            
        except Exception as e:
            logger.error(f"Error loading files: {str(e)}")
            raise
    
    def _should_exclude(self, path: str, patterns: List[str]) -> bool:
        """
        Check if path should be excluded based on patterns
        
        Args:
            path: File path to check
            patterns: List of exclusion patterns
            
        Returns:
            True if should be excluded
        """
        path_parts = Path(path).parts
        
        for pattern in patterns:
            if pattern in path_parts:
                return True
            if Path(path).match(pattern):
                return True
        
        return False
    
    def count_files(self, directory: str, 
                    extensions: Optional[List[str]] = None) -> int:
        """
        Count files in directory
        
        Args:
            directory: Directory to count files in
            extensions: List of file extensions to count
            
        Returns:
            Number of files
        """
        try:
            count = 0
            directory_path = Path(directory)
            
            for file_path in directory_path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                if extensions and file_path.suffix not in extensions:
                    continue
                
                count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"Error counting files: {str(e)}")
            return 0
    
    def save_converted_files(self, project_path: str, 
                            converted_files) -> Path:
        """
        Save converted files to disk
        
        Args:
            project_path: Project directory path
            converted_files: Dictionary of file paths to contents, or list of dicts with file info
            
        Returns:
            Path to converted files directory
        """
        try:
            # Create converted directory
            converted_path = Path(project_path) / 'converted'
            converted_path.mkdir(parents=True, exist_ok=True)
            
            # Handle both dict and list formats
            if isinstance(converted_files, list):
                # Convert list of dicts to dict format
                logger.warning("Received list instead of dict, converting...")
                files_dict = {}
                for file_info in converted_files:
                    if isinstance(file_info, dict):
                        # Get file path (prefer new_file_path, fallback to original_path)
                        file_path = file_info.get('new_file_path') or file_info.get('original_path')
                        file_content = file_info.get('converted_code')
                        
                        if file_path and file_content:
                            # Normalize path
                            file_path = file_path.lstrip('/\\').replace('\\', '/')
                            files_dict[file_path] = file_content
                converted_files = files_dict
            
            # Ensure converted_files is a dictionary
            if not isinstance(converted_files, dict):
                raise ValueError(f"converted_files must be a dictionary, got {type(converted_files)}")
            
            # Save each file
            saved_count = 0
            for file_path, content in converted_files.items():
                try:
                    # Normalize path (handle both relative and absolute paths)
                    # Remove any leading slashes or dots
                    normalized_path = file_path.lstrip('/\\').lstrip('.').lstrip('/\\')
                    
                    # Create full path
                    full_path = converted_path / normalized_path
                    
                    # Security check: ensure path is within converted_path
                    try:
                        full_path.resolve().relative_to(converted_path.resolve())
                    except ValueError:
                        logger.warning(f"Invalid file path (outside converted directory): {file_path}")
                        continue
                    
                    # Create parent directories
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write file
                    self.parser.write_file(full_path, content)
                    saved_count += 1
                    
                except Exception as e:
                    logger.error(f"Error saving file {file_path}: {str(e)}")
                    # Continue with other files even if one fails
                    continue
            
            logger.info(f"Saved {saved_count} out of {len(converted_files)} converted files to {converted_path}")
            if saved_count < len(converted_files):
                logger.warning(f"Some files could not be saved: {len(converted_files) - saved_count} files failed")
            return converted_path
            
        except Exception as e:
            logger.error(f"Error saving converted files: {str(e)}")
            raise
    
    def create_download_zip(self, source_directory: str, 
                           output_path: Optional[str] = None) -> Path:
        """
        Create ZIP file for download
        
        Args:
            source_directory: Directory to zip
            output_path: Optional output path for ZIP file
            
        Returns:
            Path to created ZIP file
        """
        try:
            source_path = Path(source_directory)
            
            if output_path is None:
                output_path = source_path.parent / f"{source_path.name}.zip"
            else:
                output_path = Path(output_path)
            
            # Create ZIP
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in source_path.rglob('*'):
                    if file_path.is_file():
                        arc_name = file_path.relative_to(source_path)
                        zipf.write(file_path, arc_name)
            
            logger.info(f"Created download ZIP: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating download ZIP: {str(e)}")
            raise
    
    def cleanup_project(self, project_path: str) -> bool:
        """
        Clean up project directory
        
        Args:
            project_path: Path to project directory
            
        Returns:
            True if successful
        """
        try:
            path = Path(project_path)
            
            if path.exists() and path.is_dir():
                shutil.rmtree(path)
                logger.info(f"Cleaned up project: {project_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cleaning up project: {str(e)}")
            return False
    
    def get_file_info(self, file_path: str) -> Dict:
        """
        Get detailed file information
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file information
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {}
            
            stat = path.stat()
            
            return {
                'name': path.name,
                'size': stat.st_size,
                'size_formatted': self._format_size(stat.st_size),
                'extension': path.suffix,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'is_file': path.is_file(),
                'is_dir': path.is_dir()
            }
            
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return {}
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def get_directory_structure(self, directory: str, 
                               max_depth: int = 3) -> Dict:
        """
        Get directory structure as nested dictionary
        
        Args:
            directory: Directory to analyze
            max_depth: Maximum depth to traverse
            
        Returns:
            Nested dictionary representing structure
        """
        try:
            return self.dir_manager.get_structure(directory, max_depth)
        except Exception as e:
            logger.error(f"Error getting directory structure: {str(e)}")
            return {}
    
    def validate_project_structure(self, directory: str) -> Tuple[bool, List[str]]:
        """
        Validate project structure
        
        Args:
            directory: Project directory
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        try:
            issues = []
            
            # Check if directory exists
            if not Path(directory).exists():
                issues.append("Directory does not exist")
                return False, issues
            
            # Check if directory is empty
            if not any(Path(directory).iterdir()):
                issues.append("Directory is empty")
                return False, issues
            
            # Check for suspicious files
            suspicious = self.validator.find_suspicious_files(directory)
            if suspicious:
                issues.append(f"Found suspicious files: {len(suspicious)}")
            
            # Check total size
            total_size = self.dir_manager.get_directory_size(directory)
            max_size = 100 * 1024 * 1024  # 100MB
            
            if total_size > max_size:
                issues.append(f"Project size exceeds limit: {self._format_size(total_size)}")
                return False, issues
            
            return len(issues) == 0, issues
            
        except Exception as e:
            logger.error(f"Error validating project: {str(e)}")
            return False, [str(e)]

