"""control_panel.py - 导航工具主控台"""
import os, sys, json
from pathlib import Path
from datetime import datetime
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QBrush
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QStackedWidget,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QInputDialog, QMessageBox, QFileDialog, QSplitter, QFrame
)

PROJECT_ROOT = Path(__file__).parent.parent
MAP_PATH = PROJECT_ROOT / "assets" / "maps" / "roco_hd_world_map.v3.png"
CUSTOM_POINTS_PATH = PROJECT_ROOT / "data" / "custom_points.json"


class MapEditorView(QGraphicsView):
    """地图编辑器视图 - 支持缩放和打点"""
    point_created = pyqtSignal(str, float, float)  # name, x, y

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_pos = None
        self._init_scene()
        self._init_ui()

    def _init_scene(self):
        """初始化场景并加载地图"""
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # 加载地图图片
        if MAP_PATH.exists():
            pixmap = QPixmap(str(MAP_PATH))
            if not pixmap.isNull():
                self.map_item = QGraphicsPixmapItem(pixmap)
                self.scene.addItem(self.map_item)
                self.setSceneRect(QRectF(pixmap.rect()))
            else:
                print(f"Warning: Failed to load map image from {MAP_PATH}")
                self.map_item = None
        else:
            print(f"Warning: Map file not found at {MAP_PATH}")
            self.map_item = None

    def _init_ui(self):
        """初始化UI设置"""
        # 设置拖拽模式为手型拖拽
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        # 设置渲染质量
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        # 设置滚动条策略
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        # 设置背景色
        self.setStyleSheet("background: #0d1117;")

    def wheelEvent(self, event):
        """滚轮缩放"""
        if event.angleDelta().y() > 0:
            self.scale(1.15, 1.15)
        else:
            self.scale(0.87, 0.87)

    def mouseDoubleClickEvent(self, event):
        """双击打点"""
        # 获取场景坐标
        scene_pos = self.mapToScene(event.pos())
        self.scene_pos = scene_pos

        # 弹出输入对话框获取点位名称
        name, ok = QInputDialog.getText(
            self,
            "创建航点",
            f"在坐标 ({int(scene_pos.x())}, {int(scene_pos.y())}) 创建航点:\n请输入航点名称:",
        )

        if ok and name.strip():
            name = name.strip()
            # 发射信号
            self.point_created.emit(name, scene_pos.x(), scene_pos.y())
            # 在场景中标记点位（可视化）
            self._mark_point(scene_pos, name)

    def _mark_point(self, pos, name):
        """在场景中标记点位"""
        # 绘制一个红色圆圈作为标记
        pen = QPen(QColor("#ff6b6b"), 3)
        brush = QBrush(QColor(255, 107, 107, 100))
        ellipse = self.scene.addEllipse(
            pos.x() - 10,
            pos.y() - 10,
            20,
            20,
            pen,
            brush
        )
        # 添加文字标签
        text = self.scene.addText(name)
        text.setDefaultTextColor(QColor("#c9d1d9"))
        text.setPos(pos.x() + 15, pos.y() - 10)


class ControlPanel(QMainWindow):
    """Roco 导航工作室主控制台"""

    def __init__(self, overlay=None, workspace_path=None):
        super().__init__()
        self.points = []  # 点位列表
        self.overlay = overlay
        self.workspace_path = workspace_path

        self._init_window()
        self._init_ui()
        self._load_existing_points()

    def _init_window(self):
        """初始化窗口属性"""
        self.setWindowTitle("Roco Navigation Studio")
        self.resize(1100, 700)

        # 应用暗黑主题 QSS
        self.setStyleSheet("""
            QMainWindow { background: #0d1117; }
            QPushButton { background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
                           padding: 8px 16px; border-radius: 6px; font-size: 13px; }
            QPushButton:hover { background: #30363d; border-color: #58a6ff; }
            QPushButton:pressed { background: #58a6ff; }
            QListWidget { background: #161b22; color: #c9d1d9; border: 1px solid #30363d;
                          border-radius: 4px; font-size: 13px; }
            QListWidget::item { padding: 6px; }
            QListWidget::item:selected { background: #21262d; color: #58a6ff; }
            QLabel { color: #c9d1d9; font-size: 13px; }
            QFrame#sidebar { background: #161b22; border-right: 1px solid #30363d; }
            QFrame#content { background: #0d1117; }
            QSplitter::handle { background: #30363d; }
            QSplitter::handle:horizontal { width: 1px; }
        """)

    def _init_ui(self):
        """初始化UI布局"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建分割器（左右分栏）
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # 左侧边栏
        self.sidebar = self._create_sidebar()
        self.sidebar.setObjectName("sidebar")
        splitter.addWidget(self.sidebar)

        # 右侧内容区
        self.content = self._create_content()
        self.content.setObjectName("content")
        splitter.addWidget(self.content)

        # 设置分割比例（左侧固定260px）
        splitter.setSizes([260, 840])

        # 设置布局
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

    def _create_sidebar(self):
        """创建左侧边栏"""
        sidebar = QFrame()
        sidebar.setMinimumWidth(260)
        sidebar.setMaximumWidth(260)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 标题
        title = QLabel("航点工作室")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #58a6ff; padding-bottom: 8px;")
        layout.addWidget(title)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #30363d;")
        layout.addWidget(line)

        # 点位列表标签
        label = QLabel("已创建点位：")
        layout.addWidget(label)

        # 点位列表
        self.point_list = QListWidget()
        self.point_list.setMinimumHeight(300)
        layout.addWidget(self.point_list)

        # 导出按钮
        export_btn = QPushButton("导出并固化点位数据")
        export_btn.clicked.connect(self._export_points)
        layout.addWidget(export_btn)

        # 清除按钮
        clear_btn = QPushButton("清除所有点位")
        clear_btn.clicked.connect(self._clear_points)
        layout.addWidget(clear_btn)

        # 底部弹性空间
        layout.addStretch()

        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.status_label)

        return sidebar

    def _create_content(self):
        """创建右侧内容区（地图编辑器）"""
        content = QFrame()

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建地图编辑器
        self.map_editor = MapEditorView()
        self.map_editor.point_created.connect(self._add_point)

        layout.addWidget(self.map_editor)

        return content

    def _add_point(self, name, x, y):
        """添加点位"""
        point_data = {
            "name": name,
            "x": int(x),
            "y": int(y),
            "type": "自定义点",
            "created_at": datetime.now().isoformat()
        }

        self.points.append(point_data)

        # 更新列表控件
        item_text = f"{name} ({int(x)}, {int(y)})"
        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, point_data)
        self.point_list.addItem(item)

        # 更新状态
        self.status_label.setText(f"已添加点位: {name}")
        print(f"[ControlPanel] 添加点位: {name} at ({int(x)}, {int(y)})")

    def _export_points(self):
        """导出点位数据到 JSON 文件"""
        if not self.points:
            QMessageBox.warning(self, "警告", "没有可导出的点位数据！")
            return

        try:
            # 确保 data 目录存在
            CUSTOM_POINTS_PATH.parent.mkdir(parents=True, exist_ok=True)

            # 写入 JSON 文件
            with open(CUSTOM_POINTS_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.points, f, ensure_ascii=False, indent=2)

            QMessageBox.information(
                self,
                "导出成功",
                f"已成功导出 {len(self.points)} 个点位到:\n{CUSTOM_POINTS_PATH}"
            )
            self.status_label.setText(f"已导出 {len(self.points)} 个点位")

        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出过程中发生错误:\n{str(e)}")
            print(f"[ControlPanel] 导出失败: {e}")

    def _clear_points(self):
        """清除所有点位"""
        if not self.points:
            return

        reply = QMessageBox.question(
            self,
            "确认清除",
            f"确定要清除所有 {len(self.points)} 个点位吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.points.clear()
            self.point_list.clear()
            self.status_label.setText("已清除所有点位")
            print("[ControlPanel] 已清除所有点位")

    def _load_existing_points(self):
        """加载已存在的点位数据"""
        if not CUSTOM_POINTS_PATH.exists():
            return

        try:
            with open(CUSTOM_POINTS_PATH, 'r', encoding='utf-8') as f:
                existing_points = json.load(f)

            if existing_points:
                for point_data in existing_points:
                    name = point_data.get("name", "未命名")
                    x = point_data.get("x", 0)
                    y = point_data.get("y", 0)
                    self._add_point(name, x, y)

                self.status_label.setText(f"已加载 {len(existing_points)} 个历史点位")
                print(f"[ControlPanel] 已加载 {len(existing_points)} 个历史点位")

        except Exception as e:
            print(f"[ControlPanel] 加载历史点位失败: {e}")
            self.status_label.setText("加载历史点位失败")


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = ControlPanel()
    window.show()
    sys.exit(app.exec_())
