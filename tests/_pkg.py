"""Load const.py/api.py by file path, bypassing the package __init__ (which needs homeassistant).

Shared by the lightweight tests that only exercise api.py and don't need
the full Home Assistant test harness.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "abacusmentalmath"


def _load(name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(f"abacusmentalmath.{name}", PKG_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_api() -> types.ModuleType:
    if "abacusmentalmath" not in sys.modules:
        pkg = types.ModuleType("abacusmentalmath")
        pkg.__path__ = [str(PKG_DIR)]
        sys.modules["abacusmentalmath"] = pkg
        _load("const")
    return sys.modules.get("abacusmentalmath.api") or _load("api")
