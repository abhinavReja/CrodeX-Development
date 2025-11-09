import os
import zipfile
import hashlib
from pathlib import Path
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Try to import magic, fall back gracefully if not available
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    logger.warning("python-magic not available, MIME type detection disabled")


class FileValidator:
    """
    Validates files and directories for security and integrity
    """
    
    # Dangerous file extensions
    DANGEROUS_EXTENSIONS = {
        '.exe', '.dll', '.so', '.dylib', '.bat', '.cmd',
        '.sh', '.ps1', '.app', '.deb', '.rpm', '.msi'
    }
    
    # Suspicious file names
    SUSPICIOUS_NAMES = {
        'malware', 'virus', 'trojan', 'keylog', 'backdoor',
        'rootkit', 'exploit', 'payload'
    }
    
    # Maximum file size (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024
    
    def is_valid_zip(self, zip_path: str) -> bool:
        """
        Validate ZIP file
        
        Args:
            zip_path: Path to ZIP file
            
        Returns:
            True if valid
        """
        try:
            # Check if file exists
            if not Path(zip_path).exists():
                logger.error(f"ZIP file not found: {zip_path}")
                return False
            
            # Check file size
            if Path(zip_path).stat().st_size > self.MAX_FILE_SIZE:
                logger.error(f"ZIP file too large: {zip_path}")
                return False
            
            # Verify it's a valid ZIP
            if not zipfile.is_zipfile(zip_path):
                logger.error(f"Not a valid ZIP file: {zip_path}")
                return False
            
            # Try to open and test the ZIP
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Test ZIP integrity
                test_result = zf.testzip()
                if test_result is not None:
                    logger.error(f"Corrupt file in ZIP: {test_result}")
                    return False
            
            return True
            
        except zipfile.BadZipFile:
            logger.error(f"Bad ZIP file: {zip_path}")
            return False
        except Exception as e:
            logger.error(f"Error validating ZIP: {str(e)}")
            return False
    
    def validate_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate individual file
        
        Args:
            file_path: Path to file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if file exists
            if not file_path.exists():
                return False, "File does not exist"
            
            # Check file size
            if file_path.stat().st_size > self.MAX_FILE_SIZE:
                return False, "File too large"
            
            # Check for dangerous extensions
            if file_path.suffix.lower() in self.DANGEROUS_EXTENSIONS:
                return False, f"Dangerous file extension: {file_path.suffix}"
            
            # Check for suspicious names
            file_name_lower = file_path.name.lower()
            for suspicious in self.SUSPICIOUS_NAMES:
                if suspicious in file_name_lower:
                    return False, f"Suspicious file name: {file_path.name}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating file {file_path}: {str(e)}")
            return False, str(e)
    
    def find_suspicious_files(self, directory: str) -> List[str]:
        """
        Find suspicious files in directory
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of suspicious file paths
        """
        suspicious_files = []
        directory_path = Path(directory)
        
        for file_path in directory_path.rglob('*'):
            if not file_path.is_file():
                continue
            
            is_valid, error = self.validate_file(file_path)
            if not is_valid:
                suspicious_files.append(str(file_path))
                logger.warning(f"Suspicious file: {file_path} - {error}")
        
        return suspicious_files
    
    def calculate_checksum(self, file_path: Path, 
                          algorithm: str = 'sha256') -> str:
        """
        Calculate file checksum
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm to use
            
        Returns:
            Hexadecimal checksum string
        """
        try:
            hash_func = hashlib.new(algorithm)
            
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_func.update(chunk)
            
            return hash_func.hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculating checksum: {str(e)}")
            return ""
    
    def verify_file_integrity(self, file_path: Path, 
                             expected_checksum: str,
                             algorithm: str = 'sha256') -> bool:
        """
        Verify file integrity using checksum
        
        Args:
            file_path: Path to file
            expected_checksum: Expected checksum value
            algorithm: Hash algorithm used
            
        Returns:
            True if checksums match
        """
        actual_checksum = self.calculate_checksum(file_path, algorithm)
        return actual_checksum == expected_checksum
    
    def get_mime_type(self, file_path: Path) -> str:
        """
        Get MIME type of file
        
        Args:
            file_path: Path to file
            
        Returns:
            MIME type string
        """
        if not MAGIC_AVAILABLE:
            return "unknown"
        
        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(str(file_path))
        except Exception as e:
            logger.error(f"Error getting MIME type: {str(e)}")
            return "unknown"
    
    def is_safe_path(self, base_path: Path, target_path: Path) -> bool:
        """
        Check if target path is safe (no path traversal)
        
        Args:
            base_path: Base directory
            target_path: Target path to check
            
        Returns:
            True if safe
        """
        try:
            # Resolve to absolute paths
            base = base_path.resolve()
            target = target_path.resolve()
            
            # Check if target is within base
            return str(target).startswith(str(base))
            
        except Exception as e:
            logger.error(f"Error checking path safety: {str(e)}")
            return False

