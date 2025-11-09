from __future__ import annotations
from typing import Dict, Any, List, Tuple, Set
import re
from .base_checker import BaseChecker

class SpringChecker(BaseChecker):
    def _collect_mappings_with_bases(self, java_sources: List[Tuple[str, str]]) -> Set[Tuple[str, str]]:
        out: Set[Tuple[str, str]] = set()
        for _, code in java_sources:
            bases = set()
            for m in re.finditer(r"@RequestMapping\s*\(\s*(?:value\s*=\s*)?\"([^\"]+)\"\s*\)", code):
                bases.add(m.group(1).rstrip("/"))
            ann_map = {"GET":"GetMapping","POST":"PostMapping","PUT":"PutMapping","DELETE":"DeleteMapping","PATCH":"PatchMapping"}
            for http, ann in ann_map.items():
                for mm in re.finditer(rf"@{ann}\s*\(\s*(?:value\s*=\s*)?\"([^\"]+)\"\s*\)", code):
                    leaf = mm.group(1)
                    if bases:
                        for b in bases:
                            path = f"{b}/{leaf}".replace("//", "/")
                            out.add((http, path if path.startswith("/") else "/" + path))
                    else:
                        p = leaf if leaf.startswith("/") else "/" + leaf
                        out.add((http, p))
        return out

    def check(self, converted_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        paths = self.paths_set(converted_files)
        java_sources = self.collect_code(converted_files, ".java")

        if not any(p.endswith("pom.xml") or p.endswith("build.gradle") for p in paths):
            issues.append({"missing": "pom.xml or build.gradle"})
        if not any(p == "src/main/resources/application.properties" or "src/main/resources/application.properties" in p for p in paths):
            issues.append({"missing": "src/main/resources/application.properties"})
        if any("@RestController" in c for _, c in java_sources) and not any(p.startswith("src/main/java/") for p in paths):
            issues.append({"missing": "src/main/java/ source tree"})
        if not any("@SpringBootApplication" in c for _, c in java_sources):
            issues.append({"missing": "Application.java with @SpringBootApplication"})

        intended = {(m, p.rstrip("/")) for (m, p) in self.intended_endpoints()}
        found_leaf = self.find_spring_mappings(java_sources)
        found_with_bases = self._collect_mappings_with_bases(java_sources)
        found = {(m, p.rstrip("/")) for (m, p) in (found_leaf | found_with_bases)}

        for m, p in intended:
            if (m, p) not in found:
                issues.append({"endpoint_missing": f"{m} {p}"})

        return {"ok": len(issues) == 0, "issues": issues}

    def suggest_repair_instructions(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "target": "spring-boot",
            "must_fix": issues,
            "reminder": (
                "Provide pom.xml or build.gradle; add Application.java annotated @SpringBootApplication; "
                "ensure src/main/java and src/main/resources exist; "
                "match IR endpoints using @RequestMapping at class and @GetMapping/@PostMapping at methods with exact paths."
            ),
        }
