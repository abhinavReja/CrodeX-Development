
# filepath: services/ir_builder.py
from __future__ import annotations
from typing import Dict, Any, List
import re
import ast

class IRBuilder:
    """
    Builds a lightweight, language-agnostic IR (Intermediate Representation)
    from source files. Currently optimized for Python/Flask patterns,
    but emits generic structures that the RuleEngine + LLM can use.
    """

    def build(self, files: Dict[str, str]) -> Dict[str, Any]:
        endpoints: List[Dict[str, Any]] = []
        models: List[Dict[str, Any]] = []
        config: Dict[str, Any] = {}
        deps: set[str] = set()

        for path, code in (files or {}).items():
            # crude dep scan
            for imp in re.findall(r"^\s*import\s+([a-zA-Z0-9_\.]+)", code, re.M):
                deps.add(imp.split('.')[0])
            for imp in re.findall(r"^\s*from\s+([a-zA-Z0-9_\.]+)\s+import", code, re.M):
                deps.add(imp.split('.')[0])

            # Flask-like routes
            for m in re.finditer(r"@app\.route\(\s*['\"](.+?)['\"]\s*,\s*methods\s*=\s*\[(.+?)\]\s*\)", code, re.S):
                route, methods = m.group(1), m.group(2)
                method = (methods.split(',')[0] if methods else 'GET').strip().strip("'\" ")
                endpoints.append({
                    "kind": "endpoint",
                    "source": {"path": path},
                    "name": f"{method}:{route}",
                    "http": {"method": method.upper(), "path": route},
                    "inputs": [],
                    "outputs": [{"type":"application/json"}]
                })

            # Basic config hints
            if "SQLALCHEMY_DATABASE_URI" in code:
                config.setdefault("db", "sqlalchemy://...")
            if "app.config" in code and "SECRET_KEY" in code:
                config.setdefault("has_secret", True)

            # Try AST to collect top-level defs/classes
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        models.append({"name": node.name, "path": path})
            except Exception:
                pass

        return {
            "entities": endpoints,
            "models": models,
            "config": config,
            "deps": sorted(deps),
        }
