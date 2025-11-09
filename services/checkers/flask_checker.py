from __future__ import annotations
from typing import Dict, Any, List
from .base_checker import BaseChecker

class FlaskChecker(BaseChecker):
    def check(self, converted_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        paths = self.paths_set(converted_files)
        py_sources = self.collect_code(converted_files, ".py")
        if not any(p.endswith("app.py") or p.endswith("__init__.py") for p in paths):
            issues.append({"missing": "app.py or app/__init__.py"})
        if not any(p.endswith("requirements.txt") or p == "requirements.txt" for p in paths):
            issues.append({"missing": "requirements.txt"})
        intended = {(m, p) for (m, p) in self.intended_endpoints()}
        found = self.find_flask_routes(py_sources)
        for e in intended:
            if e not in found:
                issues.append({"endpoint_missing": f"{e[0]} {e[1]}"})
        return {"ok": len(issues) == 0, "issues": issues}
