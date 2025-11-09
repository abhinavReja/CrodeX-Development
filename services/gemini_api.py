import google.generativeai as genai
import os
from typing import Dict, List, Optional
import json
import re
import logging

logger = logging.getLogger(__name__)


class GeminiService:
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        genai.configure(api_key=self.api_key)
        
        # Updated to use gemini-2.0-flash-exp model
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
        self.generation_config = {
            'temperature': float(os.getenv('AI_TEMPERATURE', 0.7)),
            'top_p': float(os.getenv('AI_TOP_P', 0.95)),
            'top_k': int(os.getenv('AI_TOP_K', 40)),
            'max_output_tokens': int(os.getenv('AI_MAX_OUTPUT_TOKENS', 8192)),
        }
        
        logger.info("✅ GeminiService initialized with gemini-2.5-pro")
        
    def analyze_project_structure(self, files: Dict[str, str]) -> Dict:
        try:
            logger.info(f"Analyzing project with {len(files)} files")
            
            file_context = self._prepare_file_context(files)
            
            prompt = f"""Analyze this project and provide detailed information in STRICT JSON format.

Project Files:
{file_context}

You MUST respond with ONLY valid JSON in this EXACT format (no markdown, no extra text):
{{
    "framework": "detected_framework_name",
    "confidence": 95,
    "structure": {{
        "type": "MVC",
        "components": ["controllers", "models", "views"],
        "entry_point": "index.php"
    }},
    "dependencies": ["package1", "package2"],
    "database": {{
        "type": "mysql",
        "migrations_found": true,
        "tables": ["users", "posts"]
    }},
    "notes": "Brief observations about the project"
}}

IMPORTANT: Respond with ONLY the JSON object, no other text or formatting."""

            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            analysis_result = self._parse_json_response(response.text)
            
            logger.info(f"✅ Analysis complete: {analysis_result.get('framework', 'Unknown')}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Error analyzing project: {str(e)}")
            raise
    
    def convert_file(
        self, 
        file_path: str,
        file_content: str,
        source_framework: str,
        target_framework: str,
        project_context: Dict,
        related_files: Dict[str, str]
    ) -> Dict:
        try:
            logger.info(f"Converting: {file_path}")
            
            prompt = f"""Convert this {source_framework} file to {target_framework}.

**Original File**: {file_path}

**Project Context**:
- Purpose: {project_context.get('purpose', 'Not specified')}
- Key Features: {', '.join(project_context.get('features', []))}

**Related Files Context**:
{self._prepare_related_files_context(related_files)}

**File to Convert**:
{file_content[:5000]}


**Requirements**:
1. Maintain exact business logic
2. Follow {target_framework} best practices
3. Preserve all functionality
4. Use modern patterns
5. Handle errors appropriately

Respond with ONLY valid JSON in this format:
{{
    "converted_code": "full converted code here (properly escaped)",
    "new_file_path": "path/to/new/file.ext",
    "dependencies": ["package1", "package2"],
    "notes": "Brief conversion notes",
    "warnings": ["Warning 1", "Warning 2"]
}}

IMPORTANT: Escape special characters in converted_code properly."""

            response = self.model.generate_content(
                prompt,
                generation_config={
                    **self.generation_config,
                    'max_output_tokens': 8192
                }
            )
            
            result = self._parse_json_response(response.text)
            result['original_path'] = file_path
            
            logger.info(f"✅ Converted: {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error converting {file_path}: {str(e)}")
            return {
                'original_path': file_path,
                'converted_code': None,
                'error': str(e),
                'warnings': [f"Conversion failed: {str(e)}"]
            }
    
    def generate_migration_guide(
        self,
        source_framework: str,
        target_framework: str,
        converted_files: List[Dict],
        project_context: Dict
    ) -> str:
        try:
            logger.info("Generating migration guide")
            
            prompt = f"""Generate a comprehensive migration guide for converting from {source_framework} to {target_framework}.

**Project Context**:
{json.dumps(project_context, indent=2)}

**Conversion Summary**:
- Total Files: {len(converted_files)}
- Source: {source_framework}
- Target: {target_framework}

Create a detailed Markdown guide with:
1. Overview & Prerequisites
2. Environment Setup
3. Dependency Installation
4. Configuration Steps
5. Database Migration
6. File Structure Changes
7. Testing Strategy
8. Deployment Guide
9. Common Issues & Solutions
10. Post-Migration Checklist

Use clear formatting, code examples, and step-by-step instructions."""

            response = self.model.generate_content(
                prompt,
                generation_config={
                    **self.generation_config,
                    'max_output_tokens': 8192
                }
            )
            
            logger.info("✅ Migration guide generated")
            return response.text
            
        except Exception as e:
            logger.error(f"❌ Error generating migration guide: {str(e)}")
            return f"# Migration Guide\n\nError generating guide: {str(e)}"
    
    def batch_convert_files(
        self,
        files: Dict[str, str],
        source_framework: str,
        target_framework: str,
        project_context: Dict,
        progress_callback=None
    ) -> List[Dict]:
        try:
            converted_files = []
            convertible_files = {k: v for k, v in files.items() if self._is_convertible_file(k)}
            
            total = len(convertible_files)
            logger.info(f"Starting batch conversion: {total} files")
            
            for idx, (file_path, content) in enumerate(convertible_files.items(), 1):
                try:
                    related = self._get_related_files(file_path, files)
                    
                    result = self.convert_file(
                        file_path=file_path,
                        file_content=content,
                        source_framework=source_framework,
                        target_framework=target_framework,
                        project_context=project_context,
                        related_files=related
                    )
                    
                    converted_files.append(result)
                    
                    if progress_callback:
                        progress_callback(idx, total, file_path)
                        
                except Exception as e:
                    logger.error(f"Error converting {file_path}: {str(e)}")
                    converted_files.append({
                        'original_path': file_path,
                        'error': str(e),
                        'converted_code': None
                    })
            
            logger.info(f"✅ Batch conversion complete: {len(converted_files)} files")
            return converted_files
            
        except Exception as e:
            logger.error(f"❌ Batch conversion failed: {str(e)}")
            raise
    
    def _prepare_file_context(self, files: Dict[str, str], max_files: int = 15) -> str:
        context_parts = []
        file_count = 0
        
        priority_patterns = [
            'composer.json', 'package.json', 'requirements.txt',
            'index.php', 'app.py', 'server.js', 'main.go'
        ]
        
        for file_path, content in files.items():
            if file_count >= max_files:
                break
            
            if any(p in file_path.lower() for p in priority_patterns):
                preview = self._truncate_content(content, 800)
                context_parts.append(f"File: {file_path}\n{preview}\n")
                file_count += 1
        
        for file_path, content in files.items():
            if file_count >= max_files:
                break
            
            if not any(p in file_path.lower() for p in priority_patterns):
                preview = self._truncate_content(content, 500)
                context_parts.append(f"File: {file_path}\n{preview}\n")
                file_count += 1
        
        if len(files) > max_files:
            context_parts.append(f"... and {len(files) - max_files} more files")
        
        return "\n".join(context_parts)
    
    def _truncate_content(self, content: str, max_length: int) -> str:
        if len(content) <= max_length:
            return content
        
        truncated = content[:max_length]
        last_newline = truncated.rfind('\n')
        
        if last_newline > max_length * 0.7:
            truncated = truncated[:last_newline]
        
        return truncated + "\n... (truncated)"
    
    def _prepare_related_files_context(self, related_files: Dict[str, str]) -> str:
        if not related_files:
            return "No related files"
        
        context = []
        for path, content in list(related_files.items())[:3]:
            preview = self._truncate_content(content, 300)
            context.append(f"// {path}\n{preview}\n")
        
        return "\n".join(context)
    
    def _get_related_files(
        self, 
        file_path: str, 
        all_files: Dict[str, str], 
        max_related: int = 3
    ) -> Dict[str, str]:
        related = {}
        file_dir = os.path.dirname(file_path)
        
        for path, content in all_files.items():
            if path == file_path or len(related) >= max_related:
                continue
            
            if os.path.dirname(path) == file_dir:
                related[path] = content
        
        return related
    
    def _is_convertible_file(self, file_path: str) -> bool:
        convertible_ext = [
            '.php', '.py', '.js', '.jsx', '.ts', '.tsx',
            '.java', '.rb', '.go', '.cs', '.html', '.vue'
        ]
        
        skip_patterns = ['node_modules/', 'vendor/', '.git/', '__pycache__/']
        
        if any(p in file_path for p in skip_patterns):
            return False
        
        return any(file_path.endswith(ext) for ext in convertible_ext)
    
    def _parse_json_response(self, text: str) -> Dict:
        try:
            text = text.strip()
            return json.loads(text)
            
        except json.JSONDecodeError:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in text:
                parts = text.split("```")
                for part in parts:
                    part = part.strip()
                    if part and part.startswith('{'):
                        try:
                            return json.loads(part)
                        except:
                            continue
            
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, text, re.DOTALL)
            
            for match in matches:
                try:
                    return json.loads(match)
                except:
                    continue
            
            logger.warning("Could not parse JSON, using manual extraction")
            return self._manual_json_extraction(text)
            
        except Exception as e:
            logger.error(f"JSON parsing error: {str(e)}")
            raise ValueError(f"Could not parse response: {text[:200]}...")
    
    def _manual_json_extraction(self, text: str) -> Dict:
        result = {}
        
        framework_match = re.search(r'framework["\s:]+(["\']?)(\w+)\1', text, re.IGNORECASE)
        if framework_match:
            result['framework'] = framework_match.group(2)
        
        confidence_match = re.search(r'confidence["\s:]+(\d+)', text, re.IGNORECASE)
        if confidence_match:
            result['confidence'] = int(confidence_match.group(1))
        
        return result or {
            'error': 'Could not parse response',
            'raw_text': text[:500]
        }