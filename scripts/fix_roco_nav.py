#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 roco_navigation_system.py：添加 PROJECT_ROOT 并修复残留硬编码路径。"""

import pathlib

BASE = pathlib.Path(r"D:\github\Roco")
fp = BASE / "src" / "roco_navigation_system.py"

txt = fp.read_text(encoding="utf-8")

# ── 修复 1：在 from PIL import Image 之后插入 pathlib 和 PROJECT_ROOT ──
marker = "from PIL import Image\n"
replacement = """from PIL import Image
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

"""
if marker in txt and "PROJECT_ROOT" not in txt:
    txt = txt.replace(marker, replacement, 1)
    print("ADDED: PROJECT_ROOT definition")
else:
    print("SKIP: PROJECT_ROOT already exists or marker not found")

# ── 修复 2：第 621 行残留硬编码路径 ──
old_path = r"temp_path = os.path.join(r'D:\Roco_Navigation_Tool_Workspace', \"roco_placeholder_map.jpg\")"
new_path = '            temp_path = str(PROJECT_ROOT / "assets" / "maps" / "roco_placeholder_map.jpg")'
if old_path in txt:
    txt = txt.replace(old_path, new_path, 1)
    print("PATCHED: line 621 hardcoded path")
else:
    print("SKIP: line 621 pattern not found (already patched?)")

fp.write_text(txt, encoding="utf-8")
print("roco_navigation_system.py — done.")
