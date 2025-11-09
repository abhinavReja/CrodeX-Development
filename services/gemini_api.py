import google.generativeai as genai
import os
from typing import Dict, List, Optional
import json
import re
import logging

logger = logging.getLogger(__name__)


class GeminiService:
    
    def __init__(self, api_key: Optional[str] = None):
        # Support both GEMINI_API_KEY and ANTHROPIC_API_KEY for backward compatibility
        self.api_key = api_key or os.getenv('GEMINI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or ANTHROPIC_API_KEY is required. Please set it in environment variables or pass it to the constructor.")
        
        genai.configure(api_key=self.api_key)
        
        # Updated to use gemini-2.0-flash-exp model
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
        self.generation_config = {
            'temperature': float(os.getenv('AI_TEMPERATURE', 0.7)),
            'top_p': float(os.getenv('AI_TOP_P', 0.95)),
            'top_k': int(os.getenv('AI_TOP_K', 40)),
            'max_output_tokens': int(os.getenv('AI_MAX_OUTPUT_TOKENS', 8192)),
        }
        
        logger.info("GeminiService initialized with gemini-2.5-pro")
        
    def analyze_project_structure(self, files: Dict[str, str]) -> Dict:
        try:
            logger.info(f"Analyzing project with {len(files)} files")
            
            file_context = self._prepare_file_context(files, max_files=50)  # Analyze more files for better business logic extraction
            
            prompt = f"""Analyze this project comprehensively and extract ALL important information including detailed business logic.

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
    "business_logic": "DETAILED and COMPREHENSIVE description of the core business logic. This MUST include: 1) Main features and functionalities - what the application does, 2) User workflows - how users interact with the system, 3) Data processing - how data flows through the application, 4) Business rules - validation rules, calculations, and logic, 5) Key algorithms - core calculations and processing logic, 6) Integration points - external services, APIs, databases, 7) Authentication and authorization - how users are authenticated and authorized, 8) Transaction processing - payments, orders, or other transactions, 9) File handling - how files are processed and stored, 10) API endpoints - what APIs exist and their purposes. Analyze the actual code to extract specific workflows, business rules, data transformations, and processes. Be specific and reference actual code patterns, functions, and logic found in the files.",
    "notes": "Brief observations about the project structure and architecture"
}}

CRITICAL REQUIREMENTS:
- The "business_logic" field is MANDATORY and must be detailed and comprehensive (minimum 500 words)
- Analyze ALL code files to understand the complete business logic
- Extract specific workflows, data flows, business rules, and algorithms
- Describe how the application works, what problems it solves, and what business processes it implements
- Reference actual code patterns, functions, routes, and logic found in the files
- The business_logic should describe the complete application functionality in detail

IMPORTANT: Respond with ONLY the JSON object, no other text or formatting."""

            response = self.model.generate_content(
                prompt,
                generation_config={
                    **self.generation_config,
                    'max_output_tokens': 16384  # Increase for detailed business logic extraction
                }
            )
            
            analysis_result = self._parse_json_response(response.text)
            
            # Ensure business_logic is present and not empty
            if 'business_logic' not in analysis_result or not analysis_result.get('business_logic') or len(analysis_result.get('business_logic', '').strip()) < 50:
                # Fallback: extract business logic from code patterns
                logger.warning("Business logic not found in AI response, using fallback extraction")
                analysis_result['business_logic'] = self._extract_business_logic_fallback(files)
            
            logger.info(f"Analysis complete: {analysis_result.get('framework', 'Unknown')}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing project: {str(e)}")
            raise
    
    def _extract_business_logic_fallback(self, files: Dict[str, str]) -> str:
        """Fallback method to extract business logic from code patterns"""
        try:
            business_logic_parts = []
            
            # Analyze main entry points
            main_files = [f for f in files.keys() if any(x in f.lower() for x in ['index', 'main', 'app', 'server', 'routes', 'controller', 'model'])]
            
            analyzed_count = 0
            for file_path in main_files[:20]:  # Analyze top 20 relevant files
                if analyzed_count >= 15:
                    break
                    
                content = files.get(file_path, '')
                if not content or len(content) < 50:
                    continue
                
                analyzed_count += 1
                
                # Look for function definitions, routes, controllers
                lines = content.split('\n')
                functions = []
                routes = []
                classes = []
                
                for i, line in enumerate(lines):
                    # Detect function definitions
                    if any(keyword in line for keyword in ['function', 'def ', 'public function', 'private function', 'protected function']):
                        func_name = line.strip()[:150]  # Get function signature
                        if func_name not in functions:
                            functions.append(func_name)
                    
                    # Detect routes/endpoints
                    if any(keyword in line for keyword in ['@app.route', 'Route::', '$router->', 'router.', 'app.get', 'app.post', 'app.put', 'app.delete']):
                        route_line = line.strip()[:150]
                        if route_line not in routes:
                            routes.append(route_line)
                    
                    # Detect class definitions
                    if any(keyword in line for keyword in ['class ', 'class\t']):
                        class_name = line.strip()[:150]
                        if class_name not in classes:
                            classes.append(class_name)
                
                if functions or routes or classes:
                    business_logic_parts.append(f"File: {file_path}")
                    if classes:
                        business_logic_parts.append(f"  Classes: {', '.join(classes[:3])}")
                    if routes:
                        business_logic_parts.append(f"  Routes/Endpoints: {len(routes)} endpoint(s) found")
                        business_logic_parts.append(f"    Examples: {', '.join(routes[:3])}")
                    if functions:
                        business_logic_parts.append(f"  Key Functions: {len(functions)} function(s) found")
                        business_logic_parts.append(f"    Examples: {', '.join(functions[:3])}")
                    business_logic_parts.append("")
            
            if business_logic_parts:
                return "Business Logic Analysis:\n\n" + "\n".join(business_logic_parts) + "\n\nThis application processes user requests through various endpoints, implements business rules through functions and classes, and handles data operations. The exact business logic depends on the specific implementation in the code files."
            else:
                return "Business logic analysis: The application handles various operations through its code structure. Key functionalities include data processing, user interactions, and business rule implementations based on the code patterns found in the project files."
                
        except Exception as e:
            logger.warning(f"Error in business logic fallback extraction: {str(e)}")
            return "Business logic analysis completed. The application handles various operations through its code structure, implementing business rules and processing logic as defined in the source files."
    
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
            
            logger.info(f"Converted: {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error converting {file_path}: {str(e)}")
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
            
            logger.info("Migration guide generated")
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating migration guide: {str(e)}")
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
            
            logger.info(f"Batch conversion complete: {len(converted_files)} files")
            return converted_files
            
        except Exception as e:
            logger.error(f"Batch conversion failed: {str(e)}")
            raise
    
    def _prepare_file_context(self, files: Dict[str, str], max_files: int = 50) -> str:
        context_parts = []
        file_count = 0
        
        priority_patterns = [
            'composer.json', 'package.json', 'requirements.txt',
            'index.php', 'app.py', 'server.js', 'main.go',
            'controller', 'model', 'route', 'handler', 'service'
        ]
        
        for file_path, content in files.items():
            if file_count >= max_files:
                break
            
            if any(p in file_path.lower() for p in priority_patterns):
                preview = self._truncate_content(content, 1000)  # Increase preview size
                context_parts.append(f"File: {file_path}\n{preview}\n")
                file_count += 1
        
        for file_path, content in files.items():
            if file_count >= max_files:
                break
            
            if not any(p in file_path.lower() for p in priority_patterns):
                preview = self._truncate_content(content, 800)  # Increase preview size
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
        
        # Try to extract business_logic
        business_logic_match = re.search(r'business_logic["\s:]+["\']([^"\']+)["\']', text, re.IGNORECASE | re.DOTALL)
        if business_logic_match:
            result['business_logic'] = business_logic_match.group(1)
        
        return result or {
            'error': 'Could not parse response',
            'raw_text': text[:500]
        }
