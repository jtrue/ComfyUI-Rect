"""
@title: Rect
@nickname: Rect
@description: Rectangle selection and utilities for ComfyUI (modular).
"""
import os, sys, pkgutil, importlib, logging
import nodes

PACK_KEY = "ComfyUI-Rect"  # used for front-end assets

_PACK_DIR = os.path.dirname(os.path.realpath(__file__))
_PY_DIR   = os.path.join(_PACK_DIR, "py")
_JS_DIR   = os.path.join(_PACK_DIR, "js")

# Make ./py importable for dynamic module loading
if _PY_DIR not in sys.path:
    sys.path.append(_PY_DIR)

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

def _merge_module(mod):
    added = []
    if hasattr(mod, "NODE_CLASS_MAPPINGS"):
        NODE_CLASS_MAPPINGS.update(mod.NODE_CLASS_MAPPINGS)
        added.extend(mod.NODE_CLASS_MAPPINGS.keys())
    if hasattr(mod, "NODE_DISPLAY_NAME_MAPPINGS"):
        NODE_DISPLAY_NAME_MAPPINGS.update(mod.NODE_DISPLAY_NAME_MAPPINGS)
    logging.info(f"[Rect] loaded {mod.__name__}: {', '.join(added) or 'no nodes'}")

# Auto-load all .py files in ./py (except those starting with "_")
for _, modname, ispkg in pkgutil.iter_modules([_PY_DIR]):
    if ispkg or modname.startswith("_"):
        continue
    try:
        mod = importlib.import_module(modname)
        _merge_module(mod)
    except Exception as e:
        logging.exception(f"[Rect] failed to load '{modname}': {e}")

# Serve front-end JS for this pack
if os.path.isdir(_JS_DIR):
    nodes.EXTENSION_WEB_DIRS[PACK_KEY] = _JS_DIR

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
