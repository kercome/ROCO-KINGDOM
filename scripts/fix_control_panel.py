#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 control_panel.py 中的硬编码路径。"""

import pathlib

BASE = pathlib.Path(r"D:\github\Roco")
fp = BASE / "src" / "control_panel.py"

txt = fp.read_text(encoding="utf-8")

# 1. 添加 from pathlib import Path（在 import os 之后）
if "from pathlib import Path" not in txt:
    txt = txt.replace("import os\n", "import os\nfrom pathlib import Path\n", 1)

# 2. 在 class 定义前添加 PROJECT_ROOT
if "PROJECT_ROOT" not in txt:
    txt = txt.replace(
        "\nclass ControlPanel",
        "\nPROJECT_ROOT = Path(__file__).parent.parent\n\nclass ControlPanel",
        1
    )

# 3. 修复硬编码路径
old = 'self.workspace_path = workspace_path or r"D:\\Roco_Navigation_Tool_Workspace"'
new = '        self.workspace_path = Path(workspace_path) if workspace_path else PROJECT_ROOT'
if old in txt:
    txt = txt.replace(old, new, 1)
    print("Patched workspace_path default")
else:
    print("WARNING: old path string not found!")

fp.write_text(txt, encoding="utf-8")
print("control_panel.py patched.")
