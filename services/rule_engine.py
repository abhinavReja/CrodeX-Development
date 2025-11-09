# filepath: services/rule_engine.py
from __future__ import annotations
from typing import Dict, Any

class RuleEngine:
    """
    Produces target-specific 'rule_hints' consumed by the LLM.
    These are *deterministic* guides (no AI) that raise conversion accuracy.
    """

    def build_hints(self, source_fw: str, target_fw: str) -> Dict[str, Any]:
        s = (source_fw or "").lower()
        t = (target_fw or "").lower().replace(" ", "").replace("-", "")

        if s == "flask" and t in ("springboot", "spring"):
            return self._flask_to_spring()

        # Add more pairs over time (django->spring, express->spring, etc.)
        base = {
            "scaffold_required": True,
            "must_emit_dependencies": True,
            "path_conventions": "Respect standard target folder layout.",
            "error_handling": "Use the target's idiomatic exception/validation handling.",
        }
        return base

    def _flask_to_spring(self) -> Dict[str, Any]:
        """
        Deterministic mapping table to push LLM towards correct Spring output.
        """
        return {
            "target": "spring-boot",
            "folder_layout": {
                "java": "src/main/java/<package-path>/",
                "resources": "src/main/resources/",
                "test": "src/test/java/<package-path>/",
            },
            "must_have": [
                "src/main/java/<package-path>/Application.java (@SpringBootApplication)",
                "src/main/resources/application.properties",
                "pom.xml OR build.gradle",
            ],
            "web_stack": {
                "deps_minimal": [
                    "org.springframework.boot:spring-boot-starter-web",
                    "org.springframework.boot:spring-boot-starter-validation",
                    "org.springframework.boot:spring-boot-starter-test"
                ],
                "controller": "@RestController + @RequestMapping base",
                "mappings": {
                    "@app.route('/x', methods=['GET'])": "@GetMapping(\"/x\")",
                    "@app.route('/x', methods=['POST'])": "@PostMapping(\"/x\")",
                    "@app.route('/x', methods=['PUT'])": "@PutMapping(\"/x\")",
                    "@app.route('/x', methods=['DELETE'])": "@DeleteMapping(\"/x\")",
                    "request.args['q']": "@RequestParam(\"q\") String q",
                    "request.args.get('q')": "@RequestParam(value=\"q\", required=false) String q",
                    "request.view_args['id'] / <id>": "@PathVariable(\"id\")",
                    "request.json / request.get_json()": "@RequestBody <Dto>",
                    "return jsonify(obj), 200": "return ResponseEntity.ok(obj);",
                },
                "file_uploads": "Use @RequestParam(\"file\") MultipartFile file",
                "cors": "Optionally add @CrossOrigin on controller/class if needed",
            },
            "templates": {
                "flask": "Jinja2 (`templates/*.html`)",
                "spring": "Thymeleaf (`src/main/resources/templates/*.html`)",
                "mapping_note": "If Flask rendered templates, migrate to Thymeleaf and update placeholders."
            },
            "config_mapping": {
                "Flask config/env": "application.properties",
                "examples": [
                    "server.port=8080",
                    "spring.mvc.view.prefix=/templates/",
                    "spring.mvc.view.suffix=.html"
                ]
            },
            "db_mapping": {
                "recommend": "spring-boot-starter-data-jpa + proper datasource in application.properties if IR indicates DB",
                "entity_style": "@Entity classes, @Repository, @Service layers if business logic is non-trivial"
            },
            "testing": {
                "controller": "SpringBootTest + MockMvc"
            },
            "package_placeholder": "com.example.app",
            "notes": "Match IR endpoints EXACTLY. Keep HTTP status codes and JSON shape identical."
        }
