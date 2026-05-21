#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — Roco Navigator 主入口
启动 PyQt5 控制台面板 + 叠加层雷达窗口
"""

import sys
from pathlib import Path

# 将 src/ 加入 sys.path，使所有模块的导入路径保持一致
SRC_DIR = str(Path(__file__).parent / "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from PyQt5.QtWidgets import QApplication
from overlay_ui import OverlayUI
from control_panel import ControlPanel


def main():
    app = QApplication(sys.argv)

    # 1. 先创建雷达叠加窗口
    overlay = OverlayUI()

    # 2. 再创建控制台面板，传入 overlay 引用
    panel = ControlPanel(overlay=overlay)

    # 3. 显示两个窗口
    overlay.show()
    panel.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()