from __future__ import annotations
from typing import Dict, Any, List
from .base_checker import BaseChecker

class DjangoChecker(BaseChecker):
    def check(self, converted_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        paths = self.paths_set(converted_files)
        py_sources = self.collect_code(converted_files, ".py")
        if not any(p.endswith("manage.py") or p == "manage.py" for p in paths):
            issues.append({"missing": "manage.py"})
        intended = {(m, p.rstrip("/")) for (m, p) in self.intended_endpoints()}
        found = {(m, p.rstrip("/")) for (m, p) in self.find_django_urls(py_sources)}
        for m, p in intended:
            if (m, p) not in found:
                issues.append({"endpoint_missing": f"{m} {p}"})
        return {"ok": len(issues) == 0, "issues": issues}
