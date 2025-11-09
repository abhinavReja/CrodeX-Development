from __future__ import annotations
from typing import Dict, Any, List, Tuple, Set
import re

class BaseChecker:
    def __init__(self, ir: Dict[str, Any], target: str):
        self.ir = ir or {}
        self.target = (target or "").lower()

    def check(self, converted_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"ok": True, "issues": []}

    def suggest_repair_instructions(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "target": self.target,
            "must_fix": issues,
            "reminder": "Fix missing endpoints/scaffold; ensure paths conform to target; keep imports correct."
        }

    def intended_endpoints(self) -> List[Tuple[str, str]]:
        out = []
        for e in self.ir.get("entities", []):
            if e.get("kind") == "endpoint":
                method = (e.get("http", {}).get("method") or "GET").upper()
                path = e.get("http", {}).get("path") or "/"
                out.append((method, path))
        return out

    @staticmethod
    def paths_set(converted_files: List[Dict[str, Any]]) -> Set[str]:
        return {
            (it.get("new_file_path") or it.get("original_path") or "").replace("\\", "/")
            for it in (converted_files or [])
            if (it.get("new_file_path") or it.get("original_path"))
        }

    @staticmethod
    def collect_code(converted_files: List[Dict[str, Any]], suffix: str) -> List[Tuple[str, str]]:
        out = []
        for it in converted_files or []:
            p = (it.get("new_file_path") or it.get("original_path") or "").replace("\\", "/")
            c = it.get("converted_code") or ""
            if p.endswith(suffix) and c:
                out.append((p, c))
        return out

    @staticmethod
    def find_spring_mappings(java_sources: List[Tuple[str, str]]) -> Set[Tuple[str, str]]:
        found = set()
        ann_map = {"GET":"GetMapping","POST":"PostMapping","PUT":"PutMapping","DELETE":"DeleteMapping","PATCH":"PatchMapping"}
        for _, code in java_sources:
            for m, ann in ann_map.items():
                for mat in re.finditer(rf"@{ann}\s*\(\s*\"([^\"]+)\"\s*\)", code): found.add((m, mat.group(1)))
                for mat in re.finditer(rf"@{ann}\s*\(\s*value\s*=\s*\"([^\"]+)\"\s*\)", code): found.add((m, mat.group(1)))
        return found

    @staticmethod
    def find_flask_routes(py_sources: List[Tuple[str, str]]) -> Set[Tuple[str, str]]:
        found = set()
        for _, code in py_sources:
            for m in re.finditer(r"@app\.route\(\s*['\"]([^'\"]+)['\"]\s*(?:,\s*methods\s*=\s*\[([^\]]+)\])?", code):
                path = m.group(1)
                methods_raw = (m.group(2) or "").upper()
                methods = re.findall(r"'(GET|POST|PUT|DELETE|PATCH)'|\"(GET|POST|PUT|DELETE|PATCH)\"", methods_raw)
                flat = {a or b for (a,b) in methods} if methods else {"GET"}
                for mm in flat: found.add((mm, path))
        return found

    @staticmethod
    def find_django_urls(py_sources: List[Tuple[str, str]]) -> Set[Tuple[str, str]]:
        found = set()
        for _, code in py_sources:
            for mat in re.finditer(r"path\(\s*['\"]([^'\"]+)['\"]", code):
                path = "/" + mat.group(1).lstrip("/")
                found.add(("GET", path.rstrip("/")))
            for mat in re.finditer(r"re_path\(\s*r?['\"]\^?/?([^'\"]+?)\$?['\"]", code):
                path = "/" + mat.group(1).lstrip("/")
                found.add(("GET", path.rstrip("/")))
        return found

    @staticmethod
    def find_express_routes(js_sources: List[Tuple[str, str]]) -> Set[Tuple[str, str]]:
        found = set()
        for _, code in js_sources:
            for mat in re.finditer(r"(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]", code, flags=re.IGNORECASE):
                found.add((mat.group(1).upper(), mat.group(2)))
        return found
