# filepath: services/gemini_api.py
from __future__ import annotations
import os, json, re, logging
from typing import Dict, List, Optional, Any
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or ANTHROPIC_API_KEY is required.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-pro")
        self.generation_config = {
            "temperature": float(os.getenv("AI_TEMPERATURE", 0.4)),  # tighter
            "top_p": float(os.getenv("AI_TOP_P", 0.9)),
            "top_k": int(os.getenv("AI_TOP_K", 40)),
            "max_output_tokens": int(os.getenv("AI_MAX_OUTPUT_TOKENS", 8192)),
        }

    # ---- analyze (unchanged enough) ----
    def analyze_project_structure(self, files: Dict[str, str]) -> Dict:
        try:
            file_context = self._prepare_file_context(files, max_files=50)
            prompt = f"""You are a senior migration analyst. Analyze SOURCE code below and return ONLY JSON.

Project Files:
{file_context}

Return JSON:
{{
  "framework": "detected_framework_name",
  "confidence": 95,
  "structure": {{
    "type": "MVC|Monolith|Microservice|Other",
    "components": ["controllers","models","views","routes","services"],
    "entry_point": "file"
  }},
  "dependencies": ["dep1","dep2"],
  "database": {{
    "type": "mysql|postgres|sqlite|mongodb|unknown",
    "migrations_found": true,
    "tables": ["users","posts"]
  }},
  "business_logic": "≥500 words specific to THIS codebase (features, flows, data, rules, endpoints). Reference concrete files/routes/functions.",
  "notes": "short observations"
}}"""
            resp = self.model.generate_content(prompt, generation_config={**self.generation_config, "max_output_tokens": 16384})
            obj = self._parse_json_response(resp.text)
            if not isinstance(obj, dict):
                return {"raw_text": resp.text}
            if len((obj.get("business_logic") or "")) < 50:
                obj["business_logic"] = self._fallback_business_logic(files)
            return obj
        except Exception as e:
            logger.error(f"analysis failed: {e}")
            return {"framework": "Unknown", "confidence": 0, "error": str(e)}

    # ---- convert ----
    def convert_file(self, file_path: str, file_content: str, source_framework: str, target_framework: str,
                     project_context: Dict[str, Any], related_files: Dict[str, str]) -> Dict:
        try:
            ir_snippet = json.dumps(project_context.get("ir", {}), indent=2)[:3800]
            hints = json.dumps(project_context.get("rule_hints", {}), indent=2)
            repair = json.dumps(project_context.get("repair_instructions", {}), indent=2) if project_context.get("repair_instructions") else "null"

            prompt = f"""
You convert a {source_framework} file into {target_framework} with high fidelity.

IR (source of truth):
{ir_snippet}

RULE HINTS (strict target expectations):
{hints}

REPAIR INSTRUCTIONS (if present, MUST FIX):
{repair}

RELATED FILES (read-only, keep logic/API consistent):
{self._prepare_related_files_context(related_files)}

SOURCE FILE: {file_path}
SOURCE CONTENT (truncated):
{file_content[:5000]}

MANDATORY:
- Preserve HTTP contract: path, method, params, status codes, and JSON shape.
- Use correct target scaffold & package paths.
- If Flask used templates, emit Thymeleaf equivalents (templates/*.html) and configure in application.properties.
- Emit build files when missing (pom.xml/gradle) with correct dependencies.
- If DTO/entity is implied, create minimal class with fields/types to compile.

RETURN ONLY JSON:
{{
  "converted_code": "FULL converted code (escaped)",
  "new_file_path": "target/relative/path.ext",
  "dependencies": ["target-dep-1","target-dep-2"],
  "build_system": "maven|gradle|none",
  "build_files": [
    {{"path":"pom.xml|build.gradle|...","content":"FULL content (if created/updated)"}}
  ],
  "project_tree_additions": ["paths/you/added/"],
  "auxiliary_files": [
    {{"path":"src/main/java/com/example/app/Application.java","content":"..."}},
    {{"path":"src/main/resources/application.properties","content":"..."}}
  ],
  "notes": "brief rationale",
  "warnings": ["risks if any"]
}}"""
            resp = self.model.generate_content(prompt, generation_config={**self.generation_config, "max_output_tokens": 8192})
            obj = self._parse_json_response(resp.text)
            if not isinstance(obj, dict):
                obj = {"converted_code": None, "error": "non-json from LLM", "raw_text": resp.text}
            obj["original_path"] = file_path
            return obj
        except Exception as e:
            return {"original_path": file_path, "converted_code": None, "error": str(e)}

    def batch_convert_files(self, files: Dict[str, str], source_framework: str, target_framework: str,
                            project_context: Dict, progress_callback=None) -> List[Dict]:
        import logging
        logger = logging.getLogger(__name__)
        
        out: List[Dict[str, Any]] = []
        conv = {k: v for k, v in files.items() if self._is_convertible_file(k)}
        total = len(conv)
        
        logger.info(f"batch_convert_files: Converting {total} files from {source_framework} to {target_framework}")
        
        if progress_callback:
            try:
                progress_callback("conversion", f"Starting conversion of {total} files...")
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
        
        for i, (fp, content) in enumerate(conv.items(), 1):
            try:
                logger.debug(f"Converting file {i}/{total}: {fp}")
                item = self.convert_file(fp, content, source_framework, target_framework, project_context, self._get_related_files(fp, files))
                if not isinstance(item, dict):
                    item = {"converted_code": None, "error": "unexpected return type", "raw": str(item), "original_path": fp}
                out.append(item)
                
                if progress_callback:
                    try:
                        # Try GeminiService format first (current, total, file_path)
                        progress_callback(i, total, fp)
                    except (TypeError, Exception) as e:
                        try:
                            # Fall back to stage/message format
                            progress_callback("conversion", f"Converting {i}/{total}: {fp}")
                        except Exception as e2:
                            logger.warning(f"Progress callback failed with both formats: {e}, {e2}")
            except Exception as e:
                logger.error(f"Error converting file {fp}: {e}")
                out.append({"original_path": fp, "converted_code": None, "error": str(e)})
        
        logger.info(f"batch_convert_files: Completed conversion of {len(out)} files")
        return out

    def generate_migration_guide(self, source_framework: str, target_framework: str,
                                 converted_files: List[Dict], project_context: Dict) -> str:
        deps = sorted({d for it in (converted_files or []) for d in (it.get("dependencies") or [])})
        prompt = f"""Generate a migration guide from {source_framework} to {target_framework} with explicit install steps.

Dependencies to install: {', '.join(deps) if deps else 'none'}

Sections:
1) Overview & Prereqs
2) Install & Build (exact commands for Maven/Gradle)
3) application.properties essentials
4) Controller/Service/Repo layering notes
5) Template migration (Jinja2 → Thymeleaf) if applicable
6) Testing (MockMvc)
7) Common pitfalls & fixes
8) Checklist

Return ONLY Markdown."""
        resp = self.model.generate_content(prompt, generation_config={**self.generation_config, "max_output_tokens": 8192})
        return resp.text

    # ---- helpers (unchanged) ----
    def _prepare_file_context(self, files: Dict[str, str], max_files: int = 50) -> str:
        parts, count = [], 0
        priority = ["composer.json","package.json","requirements.txt","pom.xml","build.gradle",
                    "index.php","app.py","server.js","main.go","controller","model","route","handler","service"]
        for fp, c in files.items():
            if count >= max_files: break
            if any(p in fp.lower() for p in priority):
                parts.append(f"File: {fp}\n{self._truncate(c, 1000)}\n"); count += 1
        for fp, c in files.items():
            if count >= max_files: break
            if not any(p in fp.lower() for p in priority):
                parts.append(f"File: {fp}\n{self._truncate(c, 800)}\n"); count += 1
        if len(files) > max_files: parts.append(f"... and {len(files)-max_files} more files")
        return "\n".join(parts)

    def _truncate(self, s: str, n: int) -> str:
        if len(s) <= n: return s
        t = s[:n]; cut = t.rfind("\n")
        return (t[:cut] if cut > n*0.7 else t) + "\n... (truncated)"

    def _get_related_files(self, file_path: str, all_files: Dict[str, str], max_related: int = 3) -> Dict[str, str]:
        import os
        base = os.path.dirname(file_path)
        rel = {}
        for p, c in all_files.items():
            if p == file_path: continue
            if len(rel) >= max_related: break
            if os.path.dirname(p) == base:
                rel[p] = c
        return rel

    def _is_convertible_file(self, file_path: str) -> bool:
        exts = [".php",".py",".js",".jsx",".ts",".tsx",".java",".rb",".go",".cs",".html",".vue",".xml",".properties"]
        skip = ["node_modules/","vendor/",".git/","__pycache__/"]
        if any(x in file_path for x in skip): return False
        return any(file_path.endswith(e) for e in exts)

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        try:
            s = (text or "").strip()
            if not s: return {"raw_text": ""}
            try:
                obj = json.loads(s)
                return obj if isinstance(obj, dict) else {"raw_text": s}
            except Exception:
                pass
            if "```json" in s:
                body = s.split("```json", 1)[1].split("```", 1)[0].strip()
                try:
                    obj = json.loads(body)
                    return obj if isinstance(obj, dict) else {"raw_text": s}
                except Exception:
                    pass
            if "```" in s:
                for part in s.split("```"):
                    part = part.strip()
                    if part.startswith("{"):
                        try:
                            obj = json.loads(part)
                            if isinstance(obj, dict): return obj
                        except Exception:
                            continue
            mats = re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", s, re.DOTALL)
            for m in mats:
                try:
                    obj = json.loads(m)
                    if isinstance(obj, dict): return obj
                except Exception:
                    continue
            return {"raw_text": s}
        except Exception as e:
            return {"raw_text": (text[:500] if isinstance(text, str) else str(text))}

    def _fallback_business_logic(self, files: Dict[str, str]) -> str:
        out = []
        mains = [p for p in files if any(x in p.lower() for x in ["index","main","app","server","routes","controller","model"])]
        for fp in mains[:20]:
            c = files.get(fp, "")
            if len(c) < 50: continue
            lines = c.splitlines()
            funs, rtes, clss = [], [], []
            for ln in lines:
                if any(k in ln for k in ["function","def ","public function","private function","protected function"]):
                    sig = ln.strip()[:150]
                    if sig not in funs: funs.append(sig)
                if any(k in ln for k in ["@app.route","Route::","$router->","router.","app.get","app.post","app.put","app.delete"]):
                    rv = ln.strip()[:150]
                    if rv not in rtes: rtes.append(rv)
                if "class " in ln or "class\t" in ln:
                    nm = ln.strip()[:150]
                    if nm not in clss: clss.append(nm)
            if funs or rtes or clss:
                out.append(f"File: {fp}")
                if clss: out.append(f"  Classes: {', '.join(clss[:3])}")
                if rtes: out.append(f"  Routes: {len(rtes)} e.g. {', '.join(rtes[:3])}")
                if funs: out.append(f"  Functions: {len(funs)} e.g. {', '.join(funs[:3])}")
                out.append("")
        return "Fallback business-logic summary:\n\n" + "\n".join(out) if out else "Fallback business-logic summary."
