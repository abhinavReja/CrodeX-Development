# services/checkers/__init__.py
from __future__ import annotations
from typing import Dict, Any

from .base_checker import BaseChecker
from .spring_checker import SpringChecker
from .django_checker import DjangoChecker
from .flask_checker import FlaskChecker
from .express_checker import ExpressChecker

__all__ = [
    "BaseChecker",
    "SpringChecker",
    "DjangoChecker",
    "FlaskChecker",
    "ExpressChecker",
    "get_checker",
]

def get_checker(target_framework: str, ir: Dict[str, Any]) -> BaseChecker:
    t = (target_framework or "").lower().replace(" ", "").replace("-", "")
    if t in ("spring", "springboot"):
        return SpringChecker(ir, target_framework)
    if t == "django":
        return DjangoChecker(ir, target_framework)
    if t == "flask":
        return FlaskChecker(ir, target_framework)
    if t in ("express", "expressjs", "node", "nodejs"):
        return ExpressChecker(ir, target_framework)
    return BaseChecker(ir, target_framework)
