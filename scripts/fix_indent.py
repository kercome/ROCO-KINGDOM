#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 overlay_ui.py 和 control_panel.py 中 self.workspace_path 的多余缩进。"""

import pathlib

BASE = pathlib.Path(r"D:\github\Roco\src")

for fname in ("overlay_ui.py", "control_panel.py"):
    fp = BASE / fname
    txt = fp.read_text(encoding="utf-8")
    original = txt

    # 把 8 个空格缩进替换成 4 个空格（仅限 self.workspace_path 这一行）
    txt = txt.replace(
        "                self.workspace_path",
        "        self.workspace_path",
    )

    if txt != original:
        fp.write_text(txt, encoding="utf-8")
        print(f"FIXED: {fname}")
    else:
        print(f"UNCHANGED: {fname}")

print("Done.")
