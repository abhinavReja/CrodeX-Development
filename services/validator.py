# filepath: services/validator.py
import logging

class ConversionValidator:
    """
    Validator used by the conversion service (NOT the utils.file_validator used for ZIPs).
    Keep this lightweight and UI-friendly.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_converted(self, converted_files, target_framework: str = ""):
        """
        Accepts list[dict] or dict and performs simple presence checks based on target framework.
        Returns: {"ok": bool, "issues": [ ... ]}
        """
        paths = set()

        if isinstance(converted_files, dict):
            paths.update([str(k) for k in converted_files.keys()])

        elif isinstance(converted_files, list):
            for item in converted_files:
                if not isinstance(item, dict):
                    continue
                p = item.get("new_file_path") or item.get("original_path") or item.get("path")
                if p:
                    paths.add(str(p))

        issues = []

        t = (target_framework or "").lower().replace("-", "").replace(" ", "")
        if t in ("spring", "springboot"):
            if "pom.xml" not in paths:
                issues.append({"missing": "pom.xml"})
            # ✅ fixed bug: properly check for application.properties
            if not any("src/main/resources/application.properties" in p for p in paths):
                issues.append({"missing": "src/main/resources/application.properties"})
            if not any(p.endswith("Application.java") for p in paths):
                issues.append({"missing": "*Application.java"})

        return {"ok": len(issues) == 0, "issues": issues}
