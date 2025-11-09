# services/checkers/express_checker.py
from __future__ import annotations
from typing import Dict, Any, List
from .base_checker import BaseChecker

class ExpressChecker(BaseChecker):
    """
    Very light structural checks for Express/Node targets.
    Ensures package.json + a server entry file exist, and attempts basic route parity.
    """

    def check(self, converted_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        paths = self.paths_set(converted_files)
        js_sources = self.collect_code(converted_files, ".js") + self.collect_code(converted_files, ".ts")

        # Must-have files
        if not any(p.endswith("package.json") or p == "package.json" for p in paths):
            issues.append({"missing": "package.json"})
        if not any(p.endswith("app.js") or p.endswith("server.js") or p.endswith("index.js") for p in paths):
            issues.append({"missing": "server entry (app.js/server.js/index.js)"})

        # Endpoint parity (best-effort)
        intended = {(m, p) for (m, p) in self.intended_endpoints()}
        found = self.find_express_routes(js_sources)
        for e in intended:
            if e not in found:
                issues.append({"endpoint_missing": f"{e[0]} {e[1]}"})

        return {"ok": len(issues) == 0, "issues": issues}
