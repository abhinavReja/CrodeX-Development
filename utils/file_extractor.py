import os
import zipfile
import tarfile
import shutil
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FileExtractor:
    """
    Handles extraction of compressed files
    Supports ZIP, TAR, TAR.GZ formats
    """
    
    def extract_zip(self, zip_path: str, extract_to: str) -> Path:
        """
        Extract ZIP file
        
        Args:
            zip_path: Path to ZIP file
            extract_to: Directory to extract to
            
        Returns:
            Path to extracted directory
            
        Raises:
            ValueError: If extraction fails
        """
        try:
            zip_path = Path(zip_path)
            extract_path = Path(extract_to) / 'extracted'
            extract_path.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Check for zip bombs
                self._check_zip_safety(zip_ref)
                
                # Extract all files
                zip_ref.extractall(extract_path)
            
            # Find root directory (handle nested zips)
            root_dir = self._find_root_directory(extract_path)
            
            logger.info(f"Extracted ZIP: {zip_path} -> {root_dir}")
            return root_dir
            
        except zipfile.BadZipFile as e:
            logger.error(f"Bad ZIP file: {str(e)}")
            raise ValueError(f"Invalid ZIP file: {str(e)}")
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            raise ValueError(f"Failed to extract ZIP: {str(e)}")
    
    def extract_tar(self, tar_path: str, extract_to: str) -> Path:
        """
        Extract TAR or TAR.GZ file
        
        Args:
            tar_path: Path to TAR file
            extract_to: Directory to extract to
            
        Returns:
            Path to extracted directory
        """
        try:
            tar_path = Path(tar_path)
            extract_path = Path(extract_to) / 'extracted'
            extract_path.mkdir(parents=True, exist_ok=True)
            
            with tarfile.open(tar_path, 'r:*') as tar_ref:
                # Check for tar bombs
                self._check_tar_safety(tar_ref)
                
                # Extract all files
                tar_ref.extractall(extract_path)
            
            # Find root directory
            root_dir = self._find_root_directory(extract_path)
            
            logger.info(f"Extracted TAR: {tar_path} -> {root_dir}")
            return root_dir
            
        except tarfile.TarError as e:
            logger.error(f"Bad TAR file: {str(e)}")
            raise ValueError(f"Invalid TAR file: {str(e)}")
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            raise ValueError(f"Failed to extract TAR: {str(e)}")
    
    def _check_zip_safety(self, zip_ref: zipfile.ZipFile, 
                          max_size: int = 1000 * 1024 * 1024):
        """
        Check ZIP file for zip bombs
        
        Args:
            zip_ref: ZipFile object
            max_size: Maximum uncompressed size (default 1GB)
            
        Raises:
            ValueError: If unsafe
        """
        total_size = 0
        
        for info in zip_ref.infolist():
            total_size += info.file_size
            
            # Check for zip bombs (high compression ratio)
            if info.file_size > 0:
                ratio = info.compress_size / info.file_size
                if ratio < 0.01:  # More than 100:1 compression
                    logger.warning(f"Suspicious compression ratio in {info.filename}")
        
        if total_size > max_size:
            raise ValueError(f"ZIP file too large: {total_size} bytes")
    
    def _check_tar_safety(self, tar_ref: tarfile.TarFile,
                         max_size: int = 1000 * 1024 * 1024):
        """
        Check TAR file for tar bombs
        
        Args:
            tar_ref: TarFile object
            max_size: Maximum uncompressed size
            
        Raises:
            ValueError: If unsafe
        """
        total_size = 0
        
        for member in tar_ref.getmembers():
            total_size += member.size
            
            # Check for absolute paths
            if member.name.startswith('/'):
                raise ValueError(f"Absolute path in TAR: {member.name}")
            
            # Check for path traversal
            if '..' in member.name:
                raise ValueError(f"Path traversal in TAR: {member.name}")
        
        if total_size > max_size:
            raise ValueError(f"TAR file too large: {total_size} bytes")
    
    def _find_root_directory(self, extract_path: Path) -> Path:
        """
        Find the actual root directory after extraction
        (Handles cases where ZIP contains a single root folder)
        
        Args:
            extract_path: Path where files were extracted
            
        Returns:
            Path to root directory
        """
        items = list(extract_path.iterdir())
        
        # If only one item and it's a directory, use it as root
        if len(items) == 1 and items[0].is_dir():
            return items[0]
        
        # Otherwise, extracted path is the root
        return extract_path
    
    def get_archive_info(self, archive_path: str) -> dict:
        """
        Get information about archive file
        
        Args:
            archive_path: Path to archive
            
        Returns:
            Dictionary with archive information
        """
        try:
            path = Path(archive_path)
            
            info = {
                'name': path.name,
                'size': path.stat().st_size,
                'type': None,
                'file_count': 0
            }
            
            # Determine type and get file count
            if zipfile.is_zipfile(path):
                info['type'] = 'zip'
                with zipfile.ZipFile(path, 'r') as zf:
                    info['file_count'] = len(zf.namelist())
            elif tarfile.is_tarfile(path):
                info['type'] = 'tar'
                with tarfile.open(path, 'r:*') as tf:
                    info['file_count'] = len(tf.getnames())
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting archive info: {str(e)}")
            return {}

