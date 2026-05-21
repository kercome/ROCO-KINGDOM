#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复所有源码中的硬编码路径为相对路径。"""

import pathlib
import re

BASE = pathlib.Path(r"D:\github\Roco")

# 需要修复的文件和对应的替换规则
# 每个规则: (正则表达式, 替换字符串)
FIXES = {
    "src/coord_aligner.py": [
        (
            r'self\.json_path = json_path or r"D:\\Roco_Navigation_Tool_Workspace\\aligned_points\.json"',
            '        self.json_path = json_path or str(PROJECT_ROOT / "data" / "aligned_points.json")'
        ),
    ],
    "src/overlay_ui.py": [
        (
            r'self\.workspace_path = workspace_path or r"D:\\Roco_Navigation_Tool_Workspace"',
            '        self.workspace_path = Path(workspace_path) if workspace_path else PROJECT_ROOT / "assets" / "maps"'
        ),
    ],
    "src/control_panel.py": [
        (
            r"self\.workspace_path = workspace_path or r'D:\\Roco_Navigation_Tool_Workspace'",
            "        self.workspace_path = Path(workspace_path) if workspace_path else PROJECT_ROOT"
        ),
    ],
    "src/roco_navigation_system.py": [
        (
            r'DEFAULT_MAP_PATH = r"D:\\图片拼图工具\\roco_hd_world_map\.v3\.png"',
            'DEFAULT_MAP_PATH = str(PROJECT_ROOT / "assets" / "maps" / "roco_hd_world_map.v3.png")'
        ),
        (
            r'CONFIG_PATH = r"D:\\Roco_Navigation_Tool_Workspace\\custom_points\.json"',
            'CONFIG_PATH = str(PROJECT_ROOT / "data" / "custom_points.json")'
        ),
    ],
}


def main():
    for rel, rules in FIXES.items():
        fp = BASE / rel
        if not fp.exists():
            print(f"SKIP (not found): {rel}")
            continue

        txt = fp.read_text(encoding="utf-8")
        orig = txt

        for pattern, replacement in rules:
            txt = re.sub(pattern, replacement, txt)

        if txt != orig:
            fp.write_text(txt, encoding="utf-8")
            print(f"PATCHED: {rel}")
        else:
            print(f"NO CHANGE: {rel}")


if __name__ == "__main__":
    main()
