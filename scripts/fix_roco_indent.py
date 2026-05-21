#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 roco_navigation_system.py 中 temp_path 行的缩进。"""

import pathlib

fp = pathlib.Path(r"D:\github\Roco\src\roco_navigation_system.py")
txt = fp.read_text(encoding="utf-8")

# 目标行有多余缩进（24 空格），应改为 12 空格（与上下文对齐）
old = "                        temp_path = str(PROJECT_ROOT / \"assets\" / \"maps\" / \"roco_placeholder_map.jpg\")"
new = "            temp_path = str(PROJECT_ROOT / \"assets\" / \"maps\" / \"roco_placeholder_map.jpg\")"

if old in txt:
    txt = txt.replace(old, new, 1)
    fp.write_text(txt, encoding="utf-8")
    print("FIXED: temp_path indentation")
else:
    # 用宽松方式找
    lines = txt.splitlines()
    for i, line in enumerate(lines, 1):
        if "temp_path = str(PROJECT_ROOT" in line:
            print(f"  Found at line {i}: {repr(line)}")
            # 修复缩进
            lines[i-1] = "            " + line.lstrip()
            fp.write_text("\n".join(lines), encoding="utf-8")
            print(f"FIXED: line {i} indentation")
            break
    else:
        print("WARN: pattern not found")

print("Done.")
