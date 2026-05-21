"""
control_panel.py - 导航工具主界面控制台
独立的 PyQt5 标准 Windows 窗口，提供"点点点"操作控制。
"""

import os
from pathlib import Path
import json
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QComboBox, QCheckBox, QLabel,
    QFileDialog, QMessageBox, QGroupBox, QFrame,
)


PROJECT_ROOT = Path(__file__).parent.parent

class ControlPanel(QMainWindow):
    """导航工具主控制台。
    
    接口契约：
        ControlPanel(overlay=None, workspace_path=None)
        - overlay: OverlayUI 实例引用（可为 None，独立运行时友好降级）
        - workspace_path: 工作目录，默认 PROJECT_ROOT（项目根目录）
    """

    def __init__(self, overlay=None, workspace_path=None):
        super().__init__()
        self.overlay = overlay
        self.workspace_path = Path(workspace_path) if workspace_path else PROJECT_ROOT
        self._routes_dir = os.path.join(self.workspace_path, "routes")
        os.makedirs(self._routes_dir, exist_ok=True)

        self.setWindowTitle("导航控制台")
        self.setFixedSize(320, 400)

        self._init_ui()
        self._refresh_route_list()
        self._position_left()

    # ── 内部 UI 构建 ──────────────────────────────────────────────

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        # ---- 1. 导入路线按钮 ----
        self.btn_import = QPushButton("导入路线")
        self.btn_import.clicked.connect(self._on_import_route)
        root.addWidget(self.btn_import)

        # ---- 2. 路线选择下拉框 ----
        route_grp = QGroupBox("路线选择")
        rl = QVBoxLayout(route_grp)
        self.cmb_routes = QComboBox()
        self.cmb_routes.currentTextChanged.connect(self._on_route_selected)
        rl.addWidget(self.cmb_routes)
        root.addWidget(route_grp)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        root.addWidget(line)

        # ---- 3-5. 叠加层控制复选框 ----
        overlay_grp = QGroupBox("叠加层控制")
        ol = QVBoxLayout(overlay_grp)

        self.chk_topmost = QCheckBox("启动绝对置顶")
        self.chk_topmost.stateChanged.connect(self._on_topmost_changed)
        ol.addWidget(self.chk_topmost)

        self.chk_penetration = QCheckBox("启用鼠标穿透")
        self.chk_penetration.stateChanged.connect(self._on_penetration_changed)
        ol.addWidget(self.chk_penetration)

        self.chk_coords = QCheckBox("显示坐标文本")
        self.chk_coords.stateChanged.connect(self._on_coords_changed)
        ol.addWidget(self.chk_coords)

        root.addWidget(overlay_grp)
        root.addStretch()

        # ---- 6. 状态栏 ----
        self.status_label = QLabel("就绪")
        self.statusBar().addWidget(self.status_label)

    # ── 窗口定位 ──────────────────────────────────────────────────

    def _position_left(self):
        """将窗口靠左居中停放（垂直方向居中偏上）。"""
        screen = self.screen()
        if screen is None:
            return  # 无屏幕可用时跳过
        sg = screen.availableGeometry()
        x = sg.left() + 20                     # 距左边缘 20px
        y = sg.top() + (sg.height() - 400) // 2  # 垂直居中
        self.move(x, max(0, y))

    # ── 槽：导入路线 ──────────────────────────────────────────────

    def _on_import_route(self):
        """弹出文件对话框选择 JSON 路线文件并导入为 active_route.json。"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择路线文件", self.workspace_path,
            "JSON 文件 (*.json)",
        )
        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                route_data = json.load(f)
        except json.JSONDecodeError:
            QMessageBox.warning(self, "解析错误", "所选文件不是有效的 JSON。")
            return
        except OSError as e:
            QMessageBox.warning(self, "读取失败", str(e))
            return

        # 基础结构校验
        if "name" not in route_data or "waypoints" not in route_data:
            QMessageBox.warning(
                self, "格式错误",
                "路线文件必须包含 name 与 waypoints 字段。",
            )
            return

        # 写入 active_route.json
        route_data["loaded_at"] = datetime.now().isoformat()
        self._save_active_route(route_data)

        # 同时存入 routes/ 目录供下拉框索引
        self._save_route_copy(route_data)

        self._refresh_route_list()
        self._update_status(route_data["name"])

    # ── 槽：路线选择变更 ──────────────────────────────────────────

    def _on_route_selected(self, name):
        """当下拉框选中某条路线时写入 active_route.json。"""
        if not name:
            return
        route_file = os.path.join(self._routes_dir, f"{name}.json")
        if not os.path.exists(route_file):
            return
        try:
            with open(route_file, "r", encoding="utf-8") as f:
                route_data = json.load(f)
            route_data["loaded_at"] = datetime.now().isoformat()
            self._save_active_route(route_data)
            self._update_status(name)
        except (json.JSONDecodeError, OSError) as e:
            QMessageBox.warning(self, "加载失败", str(e))

    # ── 槽：复选框变更 ────────────────────────────────────────────

    def _on_topmost_changed(self, state):
        if self.overlay is not None:
            self.overlay.set_topmost(state == Qt.Checked)

    def _on_penetration_changed(self, state):
        if self.overlay is not None:
            self.overlay.set_penetration(state == Qt.Checked)

    def _on_coords_changed(self, state):
        if self.overlay is not None:
            self.overlay.set_show_coords(state == Qt.Checked)

    # ── 内部辅助 ──────────────────────────────────────────────────

    def _save_active_route(self, data: dict):
        active = os.path.join(self.workspace_path, "active_route.json")
        with open(active, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_route_copy(self, data: dict):
        copy = os.path.join(self._routes_dir, f"{data['name']}.json")
        with open(copy, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _refresh_route_list(self):
        """扫描 routes/ 目录，刷新下拉框。"""
        self.cmb_routes.blockSignals(True)
        try:
            self.cmb_routes.clear()
            self.cmb_routes.addItem("")   # 空占位项
            if os.path.isdir(self._routes_dir):
                for fname in sorted(os.listdir(self._routes_dir)):
                    if fname.endswith(".json"):
                        self.cmb_routes.addItem(fname[:-5])
        finally:
            self.cmb_routes.blockSignals(False)

    def _update_status(self, route_name: str):
        self.status_label.setText(f"当前路线: {route_name}")