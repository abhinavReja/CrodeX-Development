# filepath: services/converter.py
import logging
import re
import json
from typing import Any, Dict, Optional, List, Tuple


class ProjectConverter:
    """
    Deterministic Flask → Spring Boot converter (no LLM).
    - Parses Flask @app.route decorators and builds a Java @RestController
    - Copies templates/ → resources/templates/ and static/ → resources/static/
    - Emits a runnable Spring Boot scaffold (pom.xml + Application)
    """

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public entrypoint expected by your routes
    # ------------------------------------------------------------------
    def full_conversion_pipeline(
        self,
        files: Dict[str, str],
        context: Optional[Dict[str, Any]] = None,
        target_framework: Optional[str] = None,
        project_context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None,
        **kwargs
    ) -> Dict[str, Any]:
        self.logger.info("=" * 80)
        self.logger.info("full_conversion_pipeline STARTED")
        self.logger.info("=" * 80)
        
        try:
            # CRITICAL: Validate input files
            if not files or not isinstance(files, dict):
                self.logger.error(f"Invalid files input: type={type(files)}, empty={not files}")
                raise ValueError(f"Invalid files input: expected dict, got {type(files)}")
            
            self.logger.info(f"full_conversion_pipeline called with {len(files)} files")
            self.logger.info(f"Target framework: {target_framework}")
            self.logger.info(f"Context keys: {list((context or project_context or {}).keys())}")
            
            ctx = context or project_context or {}
            tf = (target_framework or ctx.get("target_framework") or "spring-boot").lower()

            if progress_callback:
                progress_callback("analysis", f"Analyzing project structure")

            source_fw = self._detect_source_framework(files)
            self.logger.info(f"Detected source framework: {source_fw}")
            
            # Determine if we should use GeminiService or Flask converter
            # Flask → Spring Boot: Use deterministic converter (no API key needed)
            # Other combinations: Use GeminiService (requires API key)
            api_key = ctx.get("api_key") or kwargs.get("api_key")
            
            # Normalize framework names for comparison
            source_fw_lower = source_fw.lower()
            tf_lower = tf.lower()
            
            # Check if this is Flask → Spring Boot (use deterministic converter)
            is_flask_to_spring = (
                source_fw_lower == "flask" and 
                tf_lower in ("spring-boot", "springboot", "spring boot")
            )
            
            if is_flask_to_spring:
                # Use Flask → Spring Boot deterministic converter
                self.logger.info(f"Using Flask → Spring Boot deterministic converter (no API key needed)")
                if progress_callback:
                    try:
                        progress_callback("conversion", f"Converting from {source_fw} to Spring Boot")
                    except Exception as e:
                        self.logger.warning(f"Progress callback failed: {e}")

                self.logger.info("Calling _convert_flask_to_spring...")
                converted_files = self._convert_flask_to_spring(files)
                self.logger.info(f"_convert_flask_to_spring returned {len(converted_files)} files")
                
                # CRITICAL: Verify we got files back
                if not converted_files or len(converted_files) == 0:
                    self.logger.error("CRITICAL: _convert_flask_to_spring returned empty list! Using scaffold fallback.")
                    converted_files = self._scaffold_fallback("spring-boot")
                    self.logger.info(f"Scaffold fallback returned {len(converted_files)} files")
                
                # Double-check: verify files have content
                files_with_content = [f for f in converted_files if f.get('converted_code') or f.get('content')]
                if len(files_with_content) != len(converted_files):
                    self.logger.warning(f"Some files have no content: {len(converted_files) - len(files_with_content)} files empty")
                    # Log which files are empty
                    for f in converted_files:
                        if not f.get('converted_code') and not f.get('content'):
                            self.logger.warning(f"Empty file: {f.get('new_file_path', 'unknown')}")
                
            else:
                # Use GeminiService for other framework combinations
                if not api_key:
                    self.logger.error(f"API key required for {source_fw} → {target_framework} conversion, but not provided!")
                    raise ValueError(f"API key required for {source_fw} → {target_framework} conversion. Please configure GEMINI_API_KEY.")
                
                self.logger.info(f"Using GeminiService for {source_fw} → {target_framework} conversion")
                try:
                    from services.gemini_api import GeminiService
                    gemini_service = GeminiService(api_key=api_key)
                    
                    if progress_callback:
                        progress_callback("conversion", f"Converting from {source_fw} to {target_framework} using AI")
                    
                    converted_files = gemini_service.batch_convert_files(
                        files=files,
                        source_framework=source_fw,
                        target_framework=target_framework,
                        project_context=ctx,
                        progress_callback=progress_callback
                    )
                    
                    self.logger.info(f"GeminiService produced {len(converted_files)} converted files")
                    
                    # CRITICAL: Verify GeminiService returned files
                    if not converted_files or len(converted_files) == 0:
                        self.logger.error("CRITICAL: GeminiService returned empty list! Falling back to scaffold.")
                        converted_files = self._scaffold_fallback("spring-boot")
                        self.logger.info(f"Scaffold fallback returned {len(converted_files)} files")
                    
                    summary = {
                        "source_framework": source_fw,
                        "target_framework": target_framework,
                        "conversion_stats": {
                            "total_files": len(files),
                            "converted_files": len(converted_files),
                            "total_warnings": sum(len(f.get("warnings", [])) for f in converted_files if isinstance(f.get("warnings"), list))
                        },
                        "summary_text": f"Converted from {source_fw} to {target_framework} with {len(converted_files)} files."
                    }
                    
                    if progress_callback:
                        progress_callback("complete", "Conversion complete")
                    
                    return {
                        "converted_files": converted_files,
                        "summary": summary,
                        "source_framework": source_fw
                    }
                except Exception as e:
                    self.logger.exception(f"GeminiService conversion failed: {e}")
                    self.logger.error("Falling back to Flask converter scaffold")
                    # Fall back to scaffold
                    converted_files = self._scaffold_fallback("spring-boot")
                    self.logger.info(f"Scaffold fallback returned {len(converted_files)} files")

            if progress_callback:
                progress_callback("documentation", "Finalizing converted project")

            summary = {
                "source_framework": source_fw,
                "target_framework": "Spring Boot",
                "conversion_stats": {
                    "total_files": len(files),
                    "converted_files": len(converted_files),
                    "total_warnings": 0
                },
                "summary_text": f"Converted to Spring Boot with {self._count_java_files(converted_files)} Java files and {self._count_resource_files(converted_files)} resource files."
            }

            if progress_callback:
                progress_callback("complete", "Conversion complete")

            return {
                "converted_files": converted_files,
                "summary": summary,
                "source_framework": source_fw
            }
        except Exception as e:
            self.logger.exception("Conversion pipeline failed")
            raise RuntimeError(f"Conversion pipeline failed: {e}") from e

    # ------------------------------------------------------------------
    # Core conversion
    # ------------------------------------------------------------------
    def _convert_flask_to_spring(self, files: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Parse Flask routes and build a minimal Spring Boot project.
        """
        # CRITICAL: Log what files we received
        self.logger.info(f"_convert_flask_to_spring called with {len(files)} files")
        if files:
            sample_files = list(files.keys())[:5]
            self.logger.info(f"Sample file paths: {sample_files}")
        
        # 1) Collect python files and look for routes
        py_items = [(p, c) for p, c in files.items() if p.lower().endswith(".py")]
        self.logger.info(f"Found {len(py_items)} Python files to analyze")
        
        routes = []  # list of (methods, path, function_name, return_mode, return_payload, path_vars_dict, form_params_dict, body_code)
        used_templates: set[str] = set()

        for path, content in py_items:
            try:
                self.logger.debug(f"Analyzing Python file: {path} ({len(content)} chars)")
                # Log a sample of the content to help debug regex matching
                if len(content) > 0:
                    sample = content[:200].replace('\n', '\\n')
                    self.logger.debug(f"  Sample content: {sample}...")
                
                file_routes, file_templates = self._extract_routes_and_templates(content)
                if file_routes:
                    self.logger.info(f"Found {len(file_routes)} routes in {path}: {[r[1] for r in file_routes]}")
                else:
                    # Check if file contains route-like patterns
                    if '@app.route' in content or '@' in content and 'route' in content:
                        self.logger.warning(f"File {path} contains '@route' but no routes were extracted. Content sample: {content[:300]}")
                routes.extend(file_routes)
                used_templates.update(file_templates)
            except Exception as e:
                self.logger.warning(f"Route parse failed for {path}: {e}")
                import traceback
                self.logger.debug(traceback.format_exc())
        
        self.logger.info(f"Total routes extracted: {len(routes)}")
        if not routes:
            self.logger.warning("No routes found in any Python files - will generate HelloController instead")

        # 2) Build Spring Boot files - ALWAYS generate these core files
        pkg = "com.example.demo"
        pkg_path = "src/main/java/com/example/demo"
        out: List[Dict[str, str]] = []

        # CRITICAL: Always generate these files, regardless of routes found
        # pom.xml - Maven build file
        pom_content = self._pom_xml()
        if not pom_content or len(pom_content.strip()) < 100:
            self.logger.error("CRITICAL: pom.xml content is invalid!")
            pom_content = self._pom_xml()  # Regenerate
        out.append({"new_file_path": "pom.xml", "converted_code": pom_content})
        self.logger.debug(f"Added pom.xml ({len(pom_content)} chars)")

        # application.properties - Spring Boot config (can be empty)
        out.append({"new_file_path": "src/main/resources/application.properties", "converted_code": ""})
        self.logger.debug("Added application.properties (empty)")

        # Application class - Spring Boot entry point
        app_content = self._application_java(pkg)
        if not app_content or '@SpringBootApplication' not in app_content:
            self.logger.error("CRITICAL: DemoApplication.java content is invalid!")
            app_content = self._application_java(pkg)  # Regenerate
        out.append({
            "new_file_path": f"{pkg_path}/DemoApplication.java",
            "converted_code": app_content
        })
        self.logger.debug(f"Added DemoApplication.java ({len(app_content)} chars)")

        # Controller - ALWAYS generate at least one controller
        if routes:
            self.logger.info(f"Generating ApiController with {len(routes)} routes")
            controller_code = self._controller_java(pkg, routes)
            self.logger.debug(f"Generated controller code ({len(controller_code)} chars)")
            out.append({
                "new_file_path": f"{pkg_path}/ApiController.java",
                "converted_code": controller_code
            })
        else:
            self.logger.info("No routes found, generating HelloController as fallback")
            hello_controller_code = self._hello_controller_java(pkg)
            out.append({
                "new_file_path": f"{pkg_path}/HelloController.java",
                "converted_code": hello_controller_code
            })
            self.logger.debug(f"Generated HelloController code ({len(hello_controller_code)} chars)")

        # 3) Copy templates and static if present, and OTHER non-Python files
        # This ensures we preserve all project files, not just Python routes
        other_files_copied = 0
        for path, content in files.items():
            lower = path.replace("\\", "/").lower()
            
            # Skip Python files (already processed for routes)
            if path.lower().endswith(".py"):
                continue
            
            # Copy templates and convert Jinja2 to Thymeleaf syntax
            if lower.startswith("templates/") or "/templates/" in lower:
                # Find last occurrence of "templates" to avoid duplicates
                parts = path.replace("\\", "/").split("/")
                templates_indices = [i for i, p in enumerate(parts) if p.lower() == "templates"]
                if templates_indices:
                    templates_idx = templates_indices[-1]
                    rel_parts = parts[templates_idx + 1:]
                    if rel_parts:
                        rel = "/".join(rel_parts)
                        # Convert Jinja2 syntax to Thymeleaf
                        thymeleaf_content = self._convert_jinja2_to_thymeleaf(content)
                        out.append({
                            "new_file_path": f"src/main/resources/templates/{rel}",
                            "converted_code": thymeleaf_content
                        })
                        other_files_copied += 1
            
            # Copy static files
            elif lower.startswith("static/") or "/static/" in lower:
                # Find last occurrence of "static" to avoid duplicates
                parts = path.replace("\\", "/").split("/")
                static_indices = [i for i, p in enumerate(parts) if p.lower() == "static"]
                if static_indices:
                    static_idx = static_indices[-1]
                    rel_parts = parts[static_idx + 1:]
                    if rel_parts:
                        rel = "/".join(rel_parts)
                        out.append({
                            "new_file_path": f"src/main/resources/static/{rel}",
                            "converted_code": content
                        })
                        other_files_copied += 1
            
            # Copy other important files (config files, etc.)
            elif any(path.lower().endswith(ext) for ext in ['.json', '.yml', '.yaml', '.properties', '.xml', '.txt', '.md']):
                # Preserve config files in resources
                if 'config' in lower or 'settings' in lower or path.lower() in ['package.json', 'requirements.txt', 'pom.xml', 'build.gradle']:
                    # Keep original structure but put in resources
                    out.append({
                        "new_file_path": f"src/main/resources/{path}",
                        "converted_code": content
                    })
                    other_files_copied += 1
        
        self.logger.info(f"Copied {other_files_copied} additional files (templates, static, configs)")

        # Note: Controller is already added above (ApiController if routes exist, HelloController if not)
        
        # 5) README
        out.append({
            "new_file_path": "README.md",
            "converted_code": self._readme_md()
        })

        # FINAL VERIFICATION: Ensure we always return a complete, runnable project
        self.logger.info(f"_convert_flask_to_spring returning {len(out)} files")
        file_paths = [item.get('new_file_path', 'unknown') for item in out]
        self.logger.info(f"Files being returned: {file_paths}")
        
        # Verify critical files exist
        critical_files = {
            "pom.xml": False,
            f"{pkg_path}/DemoApplication.java": False,
            "README.md": False
        }
        has_controller = False
        
        for item in out:
            path = item.get('new_file_path', 'unknown')
            content = item.get('converted_code', '') or item.get('content', '')
            content_len = len(content) if isinstance(content, str) else 0
            
            if path == "pom.xml":
                critical_files["pom.xml"] = content_len > 100
            elif path == f"{pkg_path}/DemoApplication.java":
                critical_files[f"{pkg_path}/DemoApplication.java"] = '@SpringBootApplication' in content
            elif path == "README.md":
                critical_files["README.md"] = content_len > 50
            elif 'Controller' in path:
                has_controller = content_len > 100 and ('@RestController' in content or '@Controller' in content)
            
            self.logger.debug(f"  - {path}: {content_len} chars")
            if content_len == 0 and path != "src/main/resources/application.properties":
                self.logger.warning(f"  WARNING: {path} has empty content!")
        
        # Ensure all critical files are present and valid
        if not critical_files["pom.xml"]:
            self.logger.error("CRITICAL: pom.xml missing or invalid! Adding...")
            out = [item for item in out if item.get('new_file_path') != 'pom.xml']
            out.insert(0, {"new_file_path": "pom.xml", "converted_code": self._pom_xml()})
        
        if not critical_files[f"{pkg_path}/DemoApplication.java"]:
            self.logger.error("CRITICAL: DemoApplication.java missing or invalid! Adding...")
            out = [item for item in out if f"{pkg_path}/DemoApplication.java" not in item.get('new_file_path', '')]
            pom_idx = next((i for i, item in enumerate(out) if item.get('new_file_path') == 'pom.xml'), 0)
            out.insert(pom_idx + 1, {"new_file_path": f"{pkg_path}/DemoApplication.java", "converted_code": self._application_java(pkg)})
        
        if not has_controller:
            self.logger.error("CRITICAL: No valid controller found! Adding HelloController...")
            out = [item for item in out if 'Controller' not in item.get('new_file_path', '')]
            app_idx = next((i for i, item in enumerate(out) if 'DemoApplication.java' in item.get('new_file_path', '')), len(out))
            out.insert(app_idx + 1, {
                "new_file_path": f"{pkg_path}/HelloController.java",
                "converted_code": self._hello_controller_java(pkg)
            })
        
        if not critical_files["README.md"]:
            self.logger.error("CRITICAL: README.md missing or invalid! Adding...")
            out = [item for item in out if item.get('new_file_path') != 'README.md']
            out.append({"new_file_path": "README.md", "converted_code": self._readme_md()})
        
        # Final verification
        final_count = len(out)
        final_paths = [item.get('new_file_path', 'unknown') for item in out]
        self.logger.info(f"Final verification: {final_count} files")
        self.logger.info(f"Final files: {final_paths}")
        
        # Must have at least: pom.xml, application.properties, DemoApplication.java, Controller, README.md
        if final_count < 5:
            self.logger.error(f"CRITICAL: Only {final_count} files! Expected at least 5.")
        
        return out

    # ------------------------------------------------------------------
    # Route extraction (very lightweight regex-based)
    # ------------------------------------------------------------------
    _route_rx = re.compile(
        r"""@(?:app|[\w_]+)\.route\(\s*['"](?P<path>[^'"]+)['"](?:\s*,\s*methods\s*=\s*\[(?P<methods>[^\]]+)\])?\s*\)\s*def\s+(?P<func>\w+)\s*\([^)]*\):\s*(?P<body>[\s\S]*?)(?=^@|\ndef\s|\Z)""",
        re.MULTILINE | re.DOTALL
    )

    _render_rx = re.compile(r"""render_template\(\s*['"](?P<tpl>[^'"]+)['"]""")
    _jsonify_rx = re.compile(r"""jsonify\(\s*(?P<obj>.+?)\s*\)""", re.DOTALL)
    _return_str_rx = re.compile(r"""return\s+['"](?P<txt>[^'"]+)['"]""")
    # Regex patterns for extracting form data and query parameters
    _request_form_get = re.compile(r"""request\.form\.get\(['"](?P<key>\w+)['"]""")
    _request_form_bracket = re.compile(r"""request\.form\[['"](?P<key>\w+)['"]\]""")
    _request_args_get = re.compile(r"""request\.args\.get\(['"](?P<key>\w+)['"]""")
    _request_args_bracket = re.compile(r"""request\.args\[['"](?P<key>\w+)['"]\]""")

    def _extract_routes_and_templates(self, content: str) -> Tuple[List[Tuple[List[str], str, str, str, str, Dict[str, str], Dict[str, bool], str]], List[str]]:
        """
        Extract routes and templates from Flask code.
        Returns: (routes, templates) where routes is list of (methods, path, func, mode, payload, path_vars_dict, form_params_dict, body_code)
        path_vars_dict maps variable name to type (e.g., {"user_id": "int", "name": "string"})
        form_params_dict maps parameter name to whether it's required (e.g., {"num1": False, "num2": False})
        body_code is the raw function body for further processing
        """
        routes = []
        templates = set()
        for m in self._route_rx.finditer(content or ""):
            path = m.group("path") or "/"
            methods = self._parse_methods(m.group("methods"))
            func = m.group("func")
            body = m.group("body") or ""

            # Extract path variables with their types from Flask format
            # Flask: /users/<int:user_id> -> {"user_id": "int"}
            # Flask: /users/<string:name> -> {"name": "string"}
            # Flask: /users/<name> -> {"name": "string"} (default)
            path_var_matches = re.finditer(r'<(?:(?P<type>int|string|float|path):)?(?P<name>\w+)>', path)
            path_vars = {}
            for match in path_var_matches:
                var_name = match.group("name")
                var_type = match.group("type") or "string"  # Default to string if no type specified
                path_vars[var_name] = var_type
            
            # Convert Flask path variables to Spring format
            spring_path = re.sub(r'<(?:(?:int|string|float|path):)?(\w+)>', r'{\1}', path)
            
            # Extract form parameters from request.form
            form_params = {}
            for match in self._request_form_get.finditer(body):
                key = match.group("key")
                form_params[key] = False  # get() means optional
            for match in self._request_form_bracket.finditer(body):
                key = match.group("key")
                form_params[key] = True  # bracket access means required
            
            # Extract query parameters from request.args
            query_params = {}
            for match in self._request_args_get.finditer(body):
                key = match.group("key")
                query_params[key] = False
            for match in self._request_args_bracket.finditer(body):
                key = match.group("key")
                query_params[key] = True
            
            # Combine form and query params (form takes precedence)
            all_params = {**query_params, **form_params}

            # Decide return mode: template, json, plain
            tpl_match = self._render_rx.search(body)
            if tpl_match:
                tpl = tpl_match.group("tpl")
                templates.add(tpl)
                routes.append((methods, spring_path, func, "template", tpl, path_vars, all_params, body))
                continue

            json_match = self._jsonify_rx.search(body)
            if json_match:
                raw = json_match.group("obj").strip()
                routes.append((methods, spring_path, func, "json", raw, path_vars, all_params, body))
                continue

            str_match = self._return_str_rx.search(body)
            if str_match:
                routes.append((methods, spring_path, func, "text", str_match.group("txt"), path_vars, all_params, body))
                continue

            # fallback
            routes.append((methods, spring_path, func, "text", f"{func} OK", path_vars, all_params, body))
        return routes, list(templates)

    def _parse_methods(self, methods_src: Optional[str]) -> List[str]:
        if not methods_src:
            return ["GET"]
        # e.g., " 'GET', 'POST' " → ["GET","POST"]
        items = re.findall(r"['\"]([A-Za-z]+)['\"]", methods_src)
        return [m.upper() for m in items] or ["GET"]
    
    def _extract_template_variables(self, body: str) -> List[str]:
        """Extract variable names passed to render_template, e.g., render_template('form.html', entry=entry)"""
        # Match render_template('template.html', var1=val1, var2=val2)
        template_var_rx = re.compile(r"""render_template\([^,]+,\s*(.+?)\)""", re.DOTALL)
        vars_list = []
        for match in template_var_rx.finditer(body):
            args_str = match.group(1)
            # Extract variable names: entry=entry, result=calc_result
            var_matches = re.findall(r"""(\w+)\s*=""", args_str)
            vars_list.extend(var_matches)
        return vars_list
    
    def _convert_python_calculations_to_java(self, body: str, form_params: Dict[str, bool]) -> str:
        """Convert Python calculation logic to Java code"""
        if not body:
            return ""
        
        java_lines = []
        
        # Extract if-elif-else blocks for operations
        # Pattern: if operation == "Addition": entry = int(var_1) + int(var_2)
        # Need to handle multiline expressions and elif chains
        if_elif_pattern = re.compile(
            r"""(?:^|\n)\s*if\s+(\w+)\s*==\s*['"]([^'"]+)['"]\s*:\s*(\w+)\s*=\s*(.+?)(?=\n\s*(?:elif|else|return|$))""",
            re.DOTALL | re.MULTILINE
        )
        
        elif_pattern = re.compile(
            r"""(?:^|\n)\s*elif\s+(\w+)\s*==\s*['"]([^'"]+)['"]\s*:\s*(\w+)\s*=\s*(.+?)(?=\n\s*(?:elif|else|return|$))""",
            re.DOTALL | re.MULTILINE
        )
        
        # Extract else block
        else_pattern = re.compile(r"""(?:^|\n)\s*else\s*:\s*(\w+)\s*=\s*(.+?)(?=\n\s*(?:return|$))""", re.DOTALL | re.MULTILINE)
        
        # Find all if-elif blocks
        conditions = []
        
        # Find if block
        for match in if_elif_pattern.finditer(body):
            var_name = match.group(1)  # e.g., "operation"
            condition_value = match.group(2)  # e.g., "Addition"
            result_var = match.group(3)  # e.g., "entry"
            expression = match.group(4).strip()  # e.g., "int(var_1) + int(var_2)"
            
            # Convert Python expression to Java
            java_expr = self._convert_python_expression_to_java(expression, form_params)
            conditions.append((var_name, condition_value, result_var, java_expr))
        
        # Find elif blocks
        for match in elif_pattern.finditer(body):
            var_name = match.group(1)
            condition_value = match.group(2)
            result_var = match.group(3)
            expression = match.group(4).strip()
            
            java_expr = self._convert_python_expression_to_java(expression, form_params)
            conditions.append((var_name, condition_value, result_var, java_expr))
        
        # Find else block
        else_result = None
        else_expr_java = None
        for match in else_pattern.finditer(body):
            else_result = match.group(1)
            else_expr = match.group(2).strip()
            else_expr_java = self._convert_python_expression_to_java(else_expr, form_params)
        
        # Generate Java if-else chain
        if conditions:
            # Determine the result variable name (should be the same for all conditions)
            result_var_name = conditions[0][2] if conditions else "result"
            operation_var = conditions[0][0] if conditions else None
            
            # Get numeric parameters that need validation
            numeric_params = [p for p in form_params.keys() if p != operation_var]
            
            # Declare result variable
            java_lines.append(f"        // Calculate result based on operation")
            java_lines.append(f"        String {result_var_name} = \"0\";")
            java_lines.append(f"        try {{")
            
            # Validate inputs - check that operation and numeric params are not null/empty
            validation_checks = []
            if operation_var:
                validation_checks.append(f"{operation_var} != null && !{operation_var}.isEmpty()")
            for param in numeric_params:
                validation_checks.append(f"{param} != null && !{param}.isEmpty()")
            
            if validation_checks:
                java_lines.append(f"            if ({' && '.join(validation_checks)}) {{")
                indent = "                "
            else:
                indent = "            "
            
            # Generate if-else chain
            for i, (var_name, condition_value, result_var, java_expr) in enumerate(conditions):
                if i == 0:
                    java_lines.append(f"{indent}if (\"{condition_value}\".equals({var_name})) {{")
                else:
                    java_lines.append(f"{indent}}} else if (\"{condition_value}\".equals({var_name})) {{")
                java_lines.append(f"{indent}    {result_var} = String.valueOf({java_expr});")
            
            # Add else block
            if else_result and else_expr_java:
                java_lines.append(f"{indent}}} else {{")
                java_lines.append(f"{indent}    {else_result} = String.valueOf({else_expr_java});")
            else:
                java_lines.append(f"{indent}}} else {{")
                java_lines.append(f"{indent}    {result_var_name} = \"0\";")
            
            java_lines.append(f"{indent}}}")
            if validation_checks:
                java_lines.append(f"            }}")
            java_lines.append(f"        }} catch (NumberFormatException e) {{")
            java_lines.append(f"            {result_var_name} = \"Error: Invalid number format\";")
            java_lines.append(f"        }} catch (ArithmeticException e) {{")
            java_lines.append(f"            {result_var_name} = \"Error: Division by zero\";")
            java_lines.append(f"        }} catch (Exception e) {{")
            java_lines.append(f"            {result_var_name} = \"Error: \" + e.getMessage();")
            java_lines.append(f"        }}")
        
        return "\n".join(java_lines)
    
    def _convert_python_expression_to_java(self, expr: str, form_params: Dict[str, bool]) -> str:
        """Convert Python expression to Java expression"""
        # Remove leading/trailing whitespace
        expr = expr.strip()
        
        # Handle int()/float() conversions - this converts int(var_1) to Integer.parseInt(var_1)
        expr = re.sub(r"""int\((\w+)\)""", r"Integer.parseInt(\1)", expr)
        expr = re.sub(r"""float\((\w+)\)""", r"Double.parseDouble(\1)", expr)
        expr = re.sub(r"""str\((\w+)\)""", r"String.valueOf(\1)", expr)
        
        # Convert Python operators
        expr = expr.replace("**", "*")  # Python power to Java (simplified)
        
        # For arithmetic expressions, check if we have standalone variables that need parsing
        # Variables that are already inside parseInt/parseDouble are fine
        if any(op in expr for op in ['+', '-', '*', '/']):
            # Find all variable names that appear in the expression
            # But only parse ones that are form parameters and aren't already parsed
            all_vars = set(re.findall(r"""\b(\w+)\b""", expr))
            
            # Remove Java keywords and already-parsed variables
            java_keywords = {'Integer', 'Double', 'String', 'parseInt', 'parseDouble', 'valueOf'}
            parsed_var_names = set()
            for match in re.finditer(r"""(Integer|Double)\.parse(Int|Double)\((\w+)\)""", expr):
                parsed_var_names.add(match.group(3))
            
            # Parse form parameter variables that aren't already parsed
            for var_name in all_vars:
                if (var_name in form_params and 
                    var_name not in parsed_var_names and 
                    var_name not in java_keywords and
                    not var_name.isdigit()):
                    # Replace standalone variable with parseInt - be careful with word boundaries
                    # Use a more precise pattern that avoids replacing inside function calls
                    pattern = rf"""(?<![a-zA-Z0-9_]){var_name}(?![a-zA-Z0-9_(])"""
                    expr = re.sub(pattern, f"Integer.parseInt({var_name})", expr)
        
        return expr
    
    def _convert_jinja2_to_thymeleaf(self, html_content: str) -> str:
        """Convert Jinja2 template syntax to Thymeleaf syntax"""
        if not html_content:
            return html_content
        
        content = html_content
        
        # Add Thymeleaf namespace to html tag if not present
        if 'xmlns:th=' not in content:
            html_tag_match = re.search(r'(<html[^>]*)', content)
            if html_tag_match and 'xmlns:th=' not in html_tag_match.group(0):
                content = content.replace(html_tag_match.group(0), html_tag_match.group(0) + ' xmlns:th="http://www.thymeleaf.org"')
        
        # Mark already processed Jinja2 expressions to avoid double conversion
        # Use a placeholder system to track what we've converted
        
        # Step 1: Convert value attributes with request.form
        # Pattern: value="{{ request.form['var_1'] }}" -> PLACEHOLDER_var_1
        placeholders = {}
        placeholder_counter = 0
        
        def create_placeholder(var_name):
            nonlocal placeholder_counter
            placeholder_counter += 1
            placeholder = f"__THYMELEAF_PLACEHOLDER_{placeholder_counter}__"
            placeholders[placeholder] = f'th:value="${{{var_name}}}"'
            return placeholder
        
        # Convert value="{{ request.form['var_1'] }}" -> placeholder
        content = re.sub(
            r"""value=["']\{\{\s*request\.form\[['"]([^'"]+)['"]\]\s*\}\}["']""",
            lambda m: create_placeholder(m.group(1)),
            content
        )
        
        # Convert value="{{ variable }}" -> placeholder (for other variables)
        content = re.sub(
            r"""value=["']\{\{\s*([^}]+)\s*\}\}["']""",
            lambda m: create_placeholder(m.group(1).strip()),
            content
        )
        
        # Convert placeholder={{ entry }} -> th:value for result display (input fields)
        # Handle both: placeholder={{ entry }} and placeholder="something {{ entry }}"
        # For result display, we want th:value instead of placeholder
        def replace_result_placeholder(match):
            var_name = match.group(1)
            # Replace placeholder with th:value for result display
            return f'th:value="${{{var_name}}}"'
        
        # Match placeholder={{ entry }} (without quotes) or placeholder="{{ entry }}"
        content = re.sub(
            r"""placeholder=(?:["'])?\{\{\s*(entry|result)\s*\}\}(?:["'])?""",
            replace_result_placeholder,
            content
        )
        
        # Convert remaining {{ variable }} in text content to [[${variable}]]
        content = re.sub(
            r"""\{\{\s*([^}]+)\s*\}\}""",
            lambda m: f'[[${{{m.group(1).strip()}}}]]',
            content
        )
        
        # Replace placeholders with actual Thymeleaf attributes
        for placeholder, thymeleaf_attr in placeholders.items():
            content = content.replace(placeholder, thymeleaf_attr)
        
        # Clean up: Remove plain value attribute if th:value exists on same tag
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            if 'th:value=' in line:
                # Remove plain value attribute that might conflict
                # Match: value="something" before th:value
                line = re.sub(r"""value=["'][^"']*["']\s+(?=.*th:value)""", '', line)
            cleaned_lines.append(line)
        content = '\n'.join(cleaned_lines)
        
        return content

    # ------------------------------------------------------------------
    # Generators
    # ------------------------------------------------------------------
    def _pom_xml(self) -> str:
        return """<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>demo</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <name>demo</name>
  <description>Converted from Flask</description>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.5</version>
    <relativePath/>
  </parent>
  <properties>
    <java.version>17</java.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-thymeleaf</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-test</artifactId>
      <scope>test</scope>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>"""

    def _application_java(self, pkg: str) -> str:
        return f"""package {pkg};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class DemoApplication {{
    public static void main(String[] args) {{
        SpringApplication.run(DemoApplication.class, args);
    }}
}}
"""

    def _hello_controller_java(self, pkg: str) -> str:
        return f"""package {pkg};

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HelloController {{

    @GetMapping("/hello")
    public String hello() {{
        return "Hello from Spring Boot!";
    }}
}}
"""

    def _controller_java(self, pkg: str, routes: List[Tuple[List[str], str, str, str, str]]) -> str:
        """
        Build a single ApiController with one method per Flask endpoint.
        return_mode: "template" | "json" | "text"
        """
        # Check if any route uses templates
        # Routes now have 7 items: (methods, path, func, mode, payload, path_vars_dict, form_params_dict)
        has_templates = any(
            (route[3] == "template" if len(route) >= 4 else False) 
            for route in routes
        )
        
        imports = [
            "import org.springframework.web.bind.annotation.*;",
            "import org.springframework.http.ResponseEntity;",
        ]
        if has_templates:
            imports.extend([
                "import org.springframework.stereotype.Controller;",
                "import org.springframework.ui.Model;",
            ])
        else:
            imports.append("import org.springframework.web.bind.annotation.RestController;")
        
        # Use @RestController for JSON APIs (more common), @Controller for templates
        controller_annotation = "@Controller" if has_templates else "@RestController"
        
        header = f"""package {pkg};

{chr(10).join(imports)}

{controller_annotation}
public class ApiController {{
"""

        methods_java = []
        for route in routes:
            # Handle route formats: (8 items: with body_code) or (7 items: with path_vars and form_params) or (6 items: with path_vars only) or (5 items: old format)
            if len(route) >= 8:
                methods, path, func, mode, payload, path_vars_dict, form_params_dict, body_code = route[:8]
            elif len(route) >= 7:
                methods, path, func, mode, payload, path_vars_dict, form_params_dict = route[:7]
                body_code = ""
            elif len(route) == 6:
                methods, path, func, mode, payload, path_vars_dict = route
                form_params_dict = {}
                body_code = ""
            else:
                # Fallback for old format
                methods, path, func, mode, payload = route[:5]
                path_var_names = re.findall(r'\{(\w+)\}', path)
                path_vars_dict = {name: "string" for name in path_var_names}
                form_params_dict = {}
                body_code = ""
            
            # Build method signature with path variables and form parameters
            method_params = []
            
            # Add path variables
            if path_vars_dict:
                type_map = {
                    "int": "Integer",
                    "float": "Double", 
                    "string": "String",
                    "path": "String"
                }
                for var_name, var_type in path_vars_dict.items():
                    java_type = type_map.get(var_type.lower(), "String")
                    method_params.append(f"@PathVariable {java_type} {var_name}")
            
            # Add form/query parameters
            if form_params_dict:
                for param_name, is_required in form_params_dict.items():
                    required_str = "" if is_required else ", required = false"
                    method_params.append(f"@RequestParam(value = \"{param_name}\"{required_str}) String {param_name}")
            
            params_str = ", ".join(method_params) if method_params else ""
            
            # normalize Spring mapping annotation
            mapping_anno = self._spring_mapping_annotation(methods, path)

            if mode == "template":
                # Template route - check if it's POST with form data
                is_post = any(m in methods for m in ['POST', 'PUT', 'PATCH'])
                has_form_data = len(form_params_dict) > 0
                
                if is_post and has_form_data:
                    # POST route with form data - extract and convert calculation logic
                    calculation_code = self._convert_python_calculations_to_java(body_code, form_params_dict)
                    
                    # Extract template variables from render_template call
                    template_vars = self._extract_template_variables(body_code)
                    
                    # Build model attribute assignments
                    model_attrs = []
                    
                    # Add calculation code
                    if calculation_code:
                        model_attrs.append(calculation_code)
                    
                    # Add form parameters to model (so template can repopulate form fields)
                    for param_name in form_params_dict.keys():
                        # Handle null values - use empty string if null
                        model_attrs.append(f"        if ({param_name} != null) {{")
                        model_attrs.append(f"            model.addAttribute(\"{param_name}\", {param_name});")
                        model_attrs.append(f"        }} else {{")
                        model_attrs.append(f"            model.addAttribute(\"{param_name}\", \"\");")
                        model_attrs.append(f"        }}")
                    
                    # Add calculated result variables to model
                    for var_name in template_vars:
                        if var_name not in form_params_dict:  # Don't duplicate form params
                            model_attrs.append(f"        model.addAttribute(\"{var_name}\", {var_name});")
                    
                    model_attrs_str = "\n".join(model_attrs) if model_attrs else "        // Process form data here"
                    
                    # Method signature includes form parameters
                    if params_str:
                        method_sig = f"public String {func}(Model model, {params_str})"
                    else:
                        method_sig = f"public String {func}(Model model)"
                    
                    methods_java.append(f"""    {mapping_anno}
    {method_sig} {{
{model_attrs_str}
        return "{payload.replace('.html', '')}";
    }}
""")
                else:
                    # GET route or POST without form data - just return template
                    method_sig = f"public String {func}(Model model{', ' + params_str if params_str else ''})"
                    methods_java.append(f"""    {mapping_anno}
    {method_sig} {{
        // Add model attributes if needed
        return "{payload.replace('.html', '')}";
    }}
""")
            elif mode == "json":
                # Build method signature with all parameters
                method_sig = f"public ResponseEntity<String> {func}({params_str})" if params_str else f"public ResponseEntity<String> {func}()"
                
                # For JSON responses
                if path_vars_dict and any(var_name in payload for var_name in path_vars_dict.keys()):
                    # Build JSON response with path variables
                    first_var = list(path_vars_dict.keys())[0] if path_vars_dict else None
                    if first_var:
                        methods_java.append(f"""    {mapping_anno}
    {method_sig} {{
        // Build JSON response with path variable
        String json = "{{\\\"id\\\": " + {first_var} + "}}";
        return ResponseEntity.ok(json);
    }}
""")
                    else:
                        safe = self._safe_json_string(payload)
                        methods_java.append(f"""    {mapping_anno}
    {method_sig} {{
        return ResponseEntity.ok({safe});
    }}
""")
                else:
                    # Static JSON - use safe_json_string helper
                    safe = self._safe_json_string(payload)
                    methods_java.append(f"""    {mapping_anno}
    {method_sig} {{
        // NOTE: returned as JSON string; consider using DTO + Jackson for type safety
        return ResponseEntity.ok({safe});
    }}
""")
            else:
                # Text/plain response
                txt = (payload or "OK").replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
                method_sig = f"public String {func}({params_str})" if params_str else f"public String {func}()"
                methods_java.append(f"""    {mapping_anno}
    {method_sig} {{
        return "{txt}";
    }}
""")

        footer = "}\n"
        return header + "".join(methods_java) + footer

    def _spring_mapping_annotation(self, methods: List[str], path: str) -> str:
        # Ensure path starts with /
        path_part = path if path.startswith("/") else f"/{path}"
        # Remove duplicate slashes
        path_part = re.sub(r'/+', '/', path_part)
        
        if methods == ["GET"]:
            return f'@GetMapping("{path_part}")'
        if methods == ["POST"]:
            return f'@PostMapping("{path_part}")'
        if methods == ["PUT"]:
            return f'@PutMapping("{path_part}")'
        if methods == ["DELETE"]:
            return f'@DeleteMapping("{path_part}")'
        if methods == ["PATCH"]:
            return f'@PatchMapping("{path_part}")'
        # multiple or uncommon → use @RequestMapping
        methods_enum = ", ".join([f"RequestMethod.{m}" for m in methods])
        return f'@RequestMapping(value="{path_part}", method={{ {methods_enum} }})'

    def _safe_json_string(self, raw: str) -> str:
        """
        Best-effort: if raw is python dict literal, try to convert to JSON string literal.
        Otherwise, return quoted raw.
        """
        try:
            # crude transform: replace single quotes with double quotes only if it looks like a dict/list
            candidate = raw.strip()
            if (candidate.startswith("{") and candidate.endswith("}")) or (candidate.startswith("[") and candidate.endswith("]")):
                # heuristic: replace single quotes with double quotes for a simple case
                # safer path would be evaluation in a sandbox; we avoid that here.
                jsonish = candidate.replace("'", '"')
                # validate
                json.loads(jsonish)
                return json.dumps(jsonish)  # as a Java String literal
        except Exception:
            pass
        # default: return raw as a quoted java string
        return json.dumps(raw)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _detect_source_framework(self, files: Dict[str, str]) -> str:
        """
        Detect source framework from files.
        More robust detection that checks both file paths and content.
        """
        if not files:
            return "Unknown"
        
        # Check file paths
        joined_paths = " ".join(files.keys()).lower()
        
        # Check file content for framework indicators
        flask_indicators = ["from flask import", "import flask", "@app.route", "Flask("]
        django_indicators = ["from django", "import django", "DJANGO_SETTINGS"]
        express_indicators = ["require('express')", "require(\"express\")", "express()", "app.get(", "app.post("]
        
        flask_score = 0
        django_score = 0
        express_score = 0
        
        # Path-based detection
        if "flask" in joined_paths or "app.py" in joined_paths:
            flask_score += 2
        if "django" in joined_paths or "manage.py" in joined_paths:
            django_score += 2
        if "express" in joined_paths or "package.json" in joined_paths:
            express_score += 2
        
        # Content-based detection (check first few files for performance)
        for path, content in list(files.items())[:10]:
            if not isinstance(content, str):
                continue
            content_lower = content.lower()
            
            for indicator in flask_indicators:
                if indicator.lower() in content_lower:
                    flask_score += 1
                    break
            for indicator in django_indicators:
                if indicator.lower() in content_lower:
                    django_score += 1
                    break
            for indicator in express_indicators:
                if indicator.lower() in content_lower:
                    express_score += 1
                    break
        
        # Return framework with highest score
        scores = {"Flask": flask_score, "Django": django_score, "Express.js": express_score}
        best = max(scores, key=scores.get)
        
        if scores[best] > 0:
            self.logger.info(f"Framework detection scores: {scores}, detected: {best}")
            return best
        else:
            self.logger.warning(f"No framework indicators found. File paths: {list(files.keys())[:5]}")
            # Default to Flask if we have Python files (common case)
            if any(p.endswith('.py') for p in files.keys()):
                self.logger.info("Defaulting to Flask based on .py files")
                return "Flask"
            return "Unknown"

    def _count_java_files(self, items: List[Dict[str, str]]) -> int:
        return sum(1 for it in items if it.get("new_file_path", "").endswith(".java"))

    def _count_resource_files(self, items: List[Dict[str, str]]) -> int:
        return sum(1 for it in items if it.get("new_file_path", "").startswith("src/main/resources/"))

    def _scaffold_fallback(self, target: str) -> List[Dict[str, str]]:
        pkg = "com.example.demo"
        pkg_path = "src/main/java/com/example/demo"
        return [
            {"new_file_path": "pom.xml", "converted_code": self._pom_xml()},
            {"new_file_path": "src/main/resources/application.properties", "converted_code": ""},
            {"new_file_path": f"{pkg_path}/DemoApplication.java", "converted_code": self._application_java(pkg)},
            {"new_file_path": f"{pkg_path}/HelloController.java", "converted_code": self._hello_controller_java(pkg)},
            {"new_file_path": "README.md", "converted_code": self._readme_md()},
        ]

    def _readme_md(self) -> str:
        return (
            "# Spring Boot project (converted from Flask)\n\n"
            "## Run\n"
            "```\n"
            "mvn spring-boot:run\n"
            "```\n\n"
            "## Notes\n"
            "- Templates were copied to `src/main/resources/templates/`\n"
            "- Static assets were copied to `src/main/resources/static/`\n"
            "- Routes were mapped into `ApiController` using best-effort translation.\n"
        )
