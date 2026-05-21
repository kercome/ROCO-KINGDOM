#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终修复 roco_navigation_system.py：补 PROJECT_ROOT 定义 + 清硬编码路径。"""

import pathlib

fp = pathlib.Path(r"D:\github\Roco\src\roco_navigation_system.py")
txt = fp.read_text(encoding="utf-8")

# ── 修复 1：添加 from pathlib import Path（放在 import time 之后）──
if "from pathlib import Path" not in txt:
    txt = txt.replace("import time\n", "import time\nfrom pathlib import Path\n", 1)
    print("[FIX] Added 'from pathlib import Path'")

# ── 修复 2：在首次使用 PROJECT_ROOT 之前插入定义 ──
#      定义必须出现在 DEFAULT_MAP_PATH 之前（约第 37 行）
if "PROJECT_ROOT = Path(__file__).parent.parent" not in txt:
    txt = txt.replace(
        "# ================= 全局核心路径与配置 =================\n",
        "# ================= 全局核心路径与配置 =================\n"
        "PROJECT_ROOT = Path(__file__).parent.parent\n\n",
        1
    )
    print("[FIX] Added PROJECT_ROOT definition")

# ── 修复 3：第 621 行硬编码路径 ──
old_621 = r"temp_path = os.path.join(r'D:\Roco_Navigation_Tool_Workspace', \"roco_placeholder_map.jpg\")"
new_621 = '            temp_path = str(PROJECT_ROOT / "assets" / "maps" / "roco_placeholder_map.jpg")'
if old_621 in txt:
    txt = txt.replace(old_621, new_621, 1)
    print("[FIX] Patched line 621 hardcoded path")
else:
    # 尝试宽松匹配
    import re
    m = re.search(r"temp_path = os\.path\.join\(r'[^']+',\s*\"roco_placeholder_map\.jpg\"\)", txt)
    if m:
        txt = txt[:m.start()] + new_621 + txt[m.end():]
        print("[FIX] Patched line 621 (regex match)")
    else:
        print("[WARN] Line 621 pattern not found, may already be patched")

fp.write_text(txt, encoding="utf-8")
print("roco_navigation_system.py — all fixes applied.")
