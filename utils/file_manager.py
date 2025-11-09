# filepath: utils/file_manager.py
import os
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime

from utils.file_extractor import FileExtractor
from utils.file_parser import FileParser
from utils.file_validator import FileValidator
from utils.directory_manager import DirectoryManager
from utils.path_utils import PathUtils
from zipfile import ZipFile, ZIP_DEFLATED

logger = logging.getLogger(__name__)


class FileManager:
    """
    Main file management class
    Handles all file operations for the converter
    """
    def __init__(self, base_upload_path: str):
        self.base_upload_path = Path(base_upload_path)
        self.base_upload_path.mkdir(parents=True, exist_ok=True)

        self.extractor = FileExtractor()
        self.parser = FileParser()
        self.validator = FileValidator()
        self.dir_manager = DirectoryManager()
        self.path_utils = PathUtils()

        logger.info(f"FileManager initialized with base path: {self.base_upload_path}")

    # --------------------- helpers ---------------------
    @staticmethod
    def _strip_fences(text: Any) -> str:
        """Remove ``` fences and return a clean string."""
        if text is None:
            return ""
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                return ""
        s = text.strip()
        if s.startswith("```"):
            parts = [p.strip() for p in s.split("```") if p.strip()]
            if parts:
                # prefer the chunk that looks like code/XML/JSON
                parts.sort(
                    key=lambda x: int(any(k in x for k in [
                        "class ", "package ", "public ", "import ",
                        "<project", "<dependencies", "\"dependencies\"", "spring-boot", "{", "}"
                    ])),
                    reverse=True,
                )
                s = parts[0]
        return s

    @staticmethod
    def _norm_relpath(path_raw: Any) -> str:
        """Normalize to a safe relative path (forward slashes, no leading slash)."""
        path = (path_raw or "")
        if not isinstance(path, str):
            path = str(path)
        path = path.lstrip("/\\").replace("\\", "/")
        return path

    @staticmethod
    def _should_exclude(path: str, patterns: List[str]) -> bool:
        path_parts = Path(path).parts
        for pattern in patterns:
            if pattern in path_parts:
                return True
            if Path(path).match(pattern):
                return True
        return False
    # ---------------------------------------------------

    def create_project_directory(self, project_id: str) -> Path:
        project_path = self.base_upload_path / project_id
        project_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created project directory: {project_path}")
        return project_path

    def extract_zip(self, zip_path: str, extract_to: str) -> Path:
        try:
            if not self.validator.is_valid_zip(zip_path):
                raise ValueError("Invalid or corrupted ZIP file")
            extracted_path = self.extractor.extract_zip(zip_path, extract_to)
            logger.info(f"Extracted ZIP to: {extracted_path}")
            return extracted_path
        except Exception as e:
            logger.error(f"Error extracting ZIP: {str(e)}")
            raise

    def load_files(self, directory: str,
                   extensions: Optional[List[str]] = None,
                   exclude_patterns: Optional[List[str]] = None) -> Dict[str, str]:
        try:
            files_dict: Dict[str, str] = {}
            directory_path = Path(directory)

            if exclude_patterns is None:
                exclude_patterns = [
                    'node_modules', '.git', '__pycache__', '.venv',
                    'vendor', 'build', 'dist', '.next', '.cache'
                ]

            for file_path in directory_path.rglob('*'):
                if not file_path.is_file():
                    continue
                rel_path = file_path.relative_to(directory_path)
                if self._should_exclude(str(rel_path), exclude_patterns):
                    continue
                if extensions and file_path.suffix not in extensions:
                    continue
                content = self.parser.read_file(file_path)
                if content is not None:
                    files_dict[str(rel_path)] = content

            logger.info(f"Loaded {len(files_dict)} files from {directory}")
            return files_dict
        except Exception as e:
            logger.error(f"Error loading files: {str(e)}")
            raise

    def count_files(self, directory: str,
                    extensions: Optional[List[str]] = None) -> int:
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

    def _coerce_converted_to_dict(self, converted_files: Any) -> Dict[str, str]:
        """
        Accept:
          - dict: {path: content}
          - list of conversion items: each may include
              - new_file_path/original_path + converted_code
              - build_files: [{path, content}]
              - auxiliary_files: [{path, content}]
        Returns {rel_path: content}
        """
        out: Dict[str, str] = {}

        if isinstance(converted_files, dict):
            # Already mapping.
            logger.info(f"Input is a dict with {len(converted_files)} items")
            for k, v in converted_files.items():
                path = self._norm_relpath(k)
                content = self._strip_fences(v) if v else ""
                # Allow empty content - some config files are intentionally empty
                if path:
                    out[path] = content
                    logger.debug(f"Added dict item to output: {path} ({len(content)} chars)")
                else:
                    logger.warning(f"Skipping dict item with invalid path: {k}")
            logger.info(f"Dict coercion produced {len(out)} files")
            return out

        if not isinstance(converted_files, list):
            logger.warning(f"converted_files is {type(converted_files)}, expected dict or list; coercing to empty.")
            return out

        # List of dict-like items
        logger.info(f"Processing list with {len(converted_files)} items")
        for idx, item in enumerate(converted_files):
            if not isinstance(item, dict):
                logger.warning(f"Item {idx} is not a dict: {type(item)}, skipping")
                continue

            # top-level converted
            top_path = item.get('new_file_path') or item.get('original_path')
            top_code = item.get('converted_code') or item.get('content')
            
            logger.debug(f"Processing item {idx}: path={top_path}, content_type={type(top_code)}, content_len={len(top_code) if isinstance(top_code, str) else 'N/A'}")
            
            # Allow empty content for files like application.properties
            # Only skip if content is None or path is missing
            if top_path:
                if isinstance(top_code, str):
                    p = self._norm_relpath(top_path)
                    if p:
                        # Allow empty strings - some config files are intentionally empty
                        # Strip fences only if content exists and might have fences
                        c = self._strip_fences(top_code) if top_code else ""
                        out[p] = c
                        logger.debug(f"Added file to output: {p} ({len(c)} chars)")
                    else:
                        logger.warning(f"Skipping file with invalid normalized path: {top_path} (normalized: {p})")
                elif top_code is None:
                    # Content is None, create empty file
                    p = self._norm_relpath(top_path)
                    if p:
                        out[p] = ""
                        logger.debug(f"Added file with None content (empty): {p}")
                else:
                    # Try to convert to string
                    try:
                        p = self._norm_relpath(top_path)
                        if p:
                            c = str(top_code)
                            c = self._strip_fences(c) if c else ""
                            out[p] = c
                            logger.debug(f"Added file (converted to string): {p} ({len(c)} chars)")
                    except Exception as e:
                        logger.warning(f"Could not convert content to string for {top_path}: {e}")
            else:
                logger.warning(f"Skipping item {idx} with no path. Item keys: {list(item.keys()) if isinstance(item, dict) else 'N/A'}")

            # build_files
            for bf in (item.get('build_files') or []):
                if not isinstance(bf, dict):
                    continue
                p = self._norm_relpath(bf.get('path', ''))
                c_content = bf.get('content', '')
                if p:
                    # Allow empty content for build files too
                    c = self._strip_fences(c_content) if isinstance(c_content, str) else ""
                    out[p] = c
                    logger.debug(f"Added build file to output: {p} ({len(c)} chars)")

            # auxiliary_files
            for af in (item.get('auxiliary_files') or []):
                if not isinstance(af, dict):
                    continue
                p = self._norm_relpath(af.get('path', ''))
                a_content = af.get('content', '')
                if p:
                    # Allow empty content for auxiliary files too
                    c = self._strip_fences(a_content) if isinstance(a_content, str) else ""
                    out[p] = c
                    logger.debug(f"Added auxiliary file to output: {p} ({len(c)} chars)")

        return out

    def save_converted_files(self, project_path: str, converted_files: Any) -> Path:
        """
        Save converted files to disk
        - Robustly handles dict or list forms
        - Writes UTF-8, creates parents, enforces path safety
        - Ensures non-empty output by adding a README if nothing was saved
        """
        try:
            converted_path = Path(project_path) / 'converted'
            converted_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"Input to save_converted_files: type={type(converted_files)}, length={len(converted_files) if isinstance(converted_files, (list, dict)) else 'N/A'}")
            if isinstance(converted_files, list) and len(converted_files) > 0:
                logger.info(f"First few items: {converted_files[:3]}")
            elif isinstance(converted_files, dict):
                logger.info(f"Dict keys (first 10): {list(converted_files.keys())[:10]}")
            
            files_dict = self._coerce_converted_to_dict(converted_files)
            
            logger.info(f"Coerced {len(files_dict)} files from converter output. Sample paths: {list(files_dict.keys())[:10]}")
            
            if not files_dict:
                logger.error("CRITICAL: No files in files_dict after coercion! This should not happen.")
                logger.error(f"Input type: {type(converted_files)}, length: {len(converted_files) if isinstance(converted_files, (list, dict)) else 'N/A'}")
                if isinstance(converted_files, list) and len(converted_files) > 0:
                    logger.error(f"First item in list: {converted_files[0]}")
                    logger.error(f"First item keys: {list(converted_files[0].keys()) if isinstance(converted_files[0], dict) else 'N/A'}")
                    logger.error(f"First item new_file_path: {converted_files[0].get('new_file_path') if isinstance(converted_files[0], dict) else 'N/A'}")
                    logger.error(f"First item converted_code type: {type(converted_files[0].get('converted_code')) if isinstance(converted_files[0], dict) else 'N/A'}")
                    logger.error(f"First item converted_code length: {len(converted_files[0].get('converted_code')) if isinstance(converted_files[0], dict) and isinstance(converted_files[0].get('converted_code'), str) else 'N/A'}")
                return converted_path  # Return early to avoid creating empty README

            saved_count = 0
            for file_path, content in files_dict.items():
                try:
                    normalized_path = self._norm_relpath(file_path).lstrip('.')
                    full_path = converted_path / normalized_path

                    # Ensure within converted_path
                    try:
                        full_path.resolve().relative_to(converted_path.resolve())
                    except Exception:
                        logger.warning(f"Invalid file path (outside converted directory): {file_path}")
                        continue

                    full_path.parent.mkdir(parents=True, exist_ok=True)

                    # Prefer parser, fallback to Path.write_text
                    try:
                        self.parser.write_file(full_path, content)
                        logger.debug(f"Saved file via parser: {normalized_path}")
                    except Exception as e:
                        logger.debug(f"Parser failed for {normalized_path}, using write_text: {e}")
                        # Ensure content is a string
                        content_str = content if isinstance(content, str) else str(content)
                        full_path.write_text(content_str, encoding="utf-8", errors="ignore")
                        logger.debug(f"Saved file via write_text: {normalized_path}")

                    saved_count += 1
                    if saved_count <= 5:  # Log first 5 files for debugging
                        logger.info(f"Saved file [{saved_count}]: {normalized_path} ({len(content)} chars)")
                except Exception as e:
                    logger.error(f"Error saving file {file_path}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue

            # Ensure folder is not empty (avoid empty zip)
            # This should NEVER happen if converter is working correctly
            if saved_count == 0:
                logger.error("CRITICAL ERROR: No files were saved! This indicates a serious problem.")
                logger.error("Creating emergency scaffold files to prevent empty ZIP...")
                
                # Create emergency scaffold
                (converted_path / "pom.xml").write_text("""<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>demo</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.5</version>
  </parent>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
  </dependencies>
</project>""", encoding="utf-8")
                
                (converted_path / "src/main/java/com/example/demo/DemoApplication.java").write_text("""package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}""", encoding="utf-8")
                
                (converted_path / "src/main/java/com/example/demo/HelloController.java").write_text("""package com.example.demo;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HelloController {
    @GetMapping("/hello")
    public String hello() {
        return "Hello from Spring Boot!";
    }
}""", encoding="utf-8")
                
                (converted_path / "README.md").write_text(
                    "# Converted Project\n\nEmergency scaffold created. Please check logs for conversion errors.",
                    encoding="utf-8"
                )
                logger.warning("Emergency scaffold created. Original conversion likely failed.")

            logger.info(f"Saved {saved_count} out of {len(files_dict)} converted files to {converted_path}")
            if saved_count < len(files_dict):
                logger.warning(f"Some files could not be saved: {len(files_dict) - saved_count} files failed")

            return converted_path
        except Exception as e:
            logger.error(f"Error saving converted files: {str(e)}")
            raise

    def create_download_zip(self, source_directory: str,
                            output_path: Optional[str] = None) -> Path:
        """
        Create ZIP file for download
        """
        try:
            source_path = Path(source_directory)

            if output_path is None:
                output_path = source_path.parent / f"{source_path.name}.zip"
            else:
                output_path = Path(output_path)

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

    def create_zip_from_directory(self, src_dir: str, zip_path: str) -> str:
        """
        Zip the contents of src_dir to zip_path (absolute). Returns zip path.
        """
        src = Path(src_dir)
        zpath = Path(zip_path)
        zpath.parent.mkdir(parents=True, exist_ok=True)

        with ZipFile(zpath, "w", compression=ZIP_DEFLATED) as z:
            for p in src.rglob("*"):
                if p.is_file():
                    z.write(p, arcname=p.relative_to(src))

        return str(zpath.resolve())

    def cleanup_project(self, project_path: str) -> bool:
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
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def get_directory_structure(self, directory: str, max_depth: int = 3) -> Dict:
        try:
            return self.dir_manager.get_structure(directory, max_depth)
        except Exception as e:
            logger.error(f"Error getting directory structure: {str(e)}")
            return {}

    def validate_project_structure(self, directory: str) -> Tuple[bool, List[str]]:
        try:
            issues: List[str] = []
            if not Path(directory).exists():
                issues.append("Directory does not exist")
                return False, issues
            if not any(Path(directory).iterdir()):
                issues.append("Directory is empty")
                return False, issues

            suspicious = self.validator.find_suspicious_files(directory)
            if suspicious:
                issues.append(f"Found suspicious files: {len(suspicious)}")

            total_size = self.dir_manager.get_directory_size(directory)
            max_size = 100 * 1024 * 1024  # 100MB
            if total_size > max_size:
                issues.append(f"Project size exceeds limit: {self._format_size(total_size)}")
                return False, issues

            return len(issues) == 0, issues
        except Exception as e:
            logger.error(f"Error validating project: {str(e)}")
            return False, [str(e)]
