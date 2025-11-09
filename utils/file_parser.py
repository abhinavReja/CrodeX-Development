import os
import chardet
from pathlib import Path
from typing import Optional, List, Dict
import logging
import json
import yaml
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class FileParser:
    """
    Handles reading and parsing various file types
    """
    
    # Binary file extensions to skip
    BINARY_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
        '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z',
        '.exe', '.dll', '.so', '.dylib',
        '.mp3', '.mp4', '.avi', '.mov',
        '.woff', '.woff2', '.ttf', '.eot'
    }
    
    # Text file extensions
    TEXT_EXTENSIONS = {
        '.py', '.js', '.jsx', '.ts', '.tsx', '.php', '.java',
        '.c', '.cpp', '.h', '.hpp', '.cs', '.rb', '.go',
        '.html', '.htm', '.css', '.scss', '.sass', '.less',
        '.json', '.xml', '.yaml', '.yml', '.toml', '.ini',
        '.md', '.txt', '.sql', '.sh', '.bat', '.env'
    }
    
    def read_file(self, file_path: Path, 
                  encoding: Optional[str] = None) -> Optional[str]:
        """
        Read file content with automatic encoding detection
        
        Args:
            file_path: Path to file
            encoding: Optional encoding to use
            
        Returns:
            File content as string, or None if binary/error
        """
        try:
            # Skip binary files
            if file_path.suffix.lower() in self.BINARY_EXTENSIONS:
                return None
            
            # Skip files larger than 10MB
            if file_path.stat().st_size > 10 * 1024 * 1024:
                logger.warning(f"Skipping large file: {file_path}")
                return None
            
            # Auto-detect encoding if not specified
            if encoding is None:
                encoding = self._detect_encoding(file_path)
            
            # Read file
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()
            
            return content
            
        except UnicodeDecodeError:
            logger.warning(f"Could not decode file: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
    
    def write_file(self, file_path: Path, content: str, 
                   encoding: str = 'utf-8'):
        """
        Write content to file
        
        Args:
            file_path: Path to file
            content: Content to write
            encoding: Encoding to use
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            logger.debug(f"Wrote file: {file_path}")
            
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {str(e)}")
            raise
    
    def _detect_encoding(self, file_path: Path) -> str:
        """
        Detect file encoding using chardet
        
        Args:
            file_path: Path to file
            
        Returns:
            Detected encoding
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # Read first 10KB
                result = chardet.detect(raw_data)
                encoding = result.get('encoding', 'utf-8')
                
                # Default to utf-8 if detection fails
                if encoding is None:
                    encoding = 'utf-8'
                
                return encoding
                
        except Exception as e:
            logger.warning(f"Encoding detection failed for {file_path}: {str(e)}")
            return 'utf-8'
    
    def parse_json(self, file_path: Path) -> Optional[Dict]:
        """
        Parse JSON file
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Parsed JSON as dictionary
        """
        try:
            content = self.read_file(file_path)
            if content:
                return json.loads(content)
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error parsing JSON {file_path}: {str(e)}")
            return None
    
    def parse_yaml(self, file_path: Path) -> Optional[Dict]:
        """
        Parse YAML file
        
        Args:
            file_path: Path to YAML file
            
        Returns:
            Parsed YAML as dictionary
        """
        try:
            content = self.read_file(file_path)
            if content:
                return yaml.safe_load(content)
            return None
            
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in {file_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error parsing YAML {file_path}: {str(e)}")
            return None
    
    def parse_xml(self, file_path: Path) -> Optional[ET.Element]:
        """
        Parse XML file
        
        Args:
            file_path: Path to XML file
            
        Returns:
            Parsed XML as ElementTree
        """
        try:
            tree = ET.parse(file_path)
            return tree.getroot()
            
        except ET.ParseError as e:
            logger.error(f"Invalid XML in {file_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error parsing XML {file_path}: {str(e)}")
            return None
    
    def is_text_file(self, file_path: Path) -> bool:
        """
        Check if file is a text file
        
        Args:
            file_path: Path to file
            
        Returns:
            True if text file
        """
        # Check extension
        if file_path.suffix.lower() in self.TEXT_EXTENSIONS:
            return True
        
        if file_path.suffix.lower() in self.BINARY_EXTENSIONS:
            return False
        
        # Try to read as text
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)
            return True
        except:
            return False
    
    def get_file_lines(self, file_path: Path) -> int:
        """
        Count lines in file
        
        Args:
            file_path: Path to file
            
        Returns:
            Number of lines
        """
        try:
            content = self.read_file(file_path)
            if content:
                return len(content.splitlines())
            return 0
        except Exception as e:
            logger.error(f"Error counting lines in {file_path}: {str(e)}")
            return 0

