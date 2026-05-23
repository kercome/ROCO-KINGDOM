# -*- coding: utf-8 -*-
# src/control_panel.py
import os
import json
import numpy as np
from pathlib import Path
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot, QPointF
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPixmap, QImage, QPolygonF
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QListWidget, QStackedWidget, QFrame, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsSimpleTextItem, QGraphicsEllipseItem,
    QGraphicsPolygonItem, QInputDialog, QMessageBox,
    QSlider, QFileDialog, QDialog, QScrollArea
)
from capture_engine import CaptureEngine
from vision_matcher import VisionMatcher
from point_detector import PointDetector
from vision_engine import VisionEngine
from roi_selector import ROISelector

# 项目根路径
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_MAP_PATH = PROJECT_ROOT / "assets" / "maps" / "roco_hd_world_map.v3.png"
CONFIG_PATH = PROJECT_ROOT / "data" / "custom_points.json"

# ================= 现代扁平化双主题 QSS =================
LIGHT_THEME = """
QMainWindow, QStackedWidget { background-color: #f3f4f6; }
#Sidebar { background-color: #ffffff; border-right: 1px solid #e5e7eb; }
#Sidebar QPushButton { background-color: transparent; border: none; border-radius: 8px; color: #4b5563; text-align: left; padding: 12px 16px; font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 13px; font-weight: bold; }
#Sidebar QPushButton:hover { background-color: #f3f4f6; color: #111827; }
#Sidebar QPushButton:checked { background-color: #eff6ff; color: #2563eb; }
#ThemeToggle { background-color: #f9fafb; border: 1px solid #e5e7eb; color: #374151; text-align: center; }
#ThemeToggle:hover { background-color: #e5e7eb; }
#Card { background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; }
QLabel { color: #1f2937; font-family: "Microsoft YaHei UI"; }
QListWidget { background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; color: #374151; font-size: 12px; padding: 5px; outline: none; }
QListWidget::item:selected { background-color: #eff6ff; color: #2563eb; border-radius: 4px; }
#ActionBtn { background-color: #3b82f6; border: none; border-radius: 8px; color: #ffffff; font-weight: bold; padding: 12px; font-size: 13px; }
#ActionBtn:hover { background-color: #2563eb; }
#DangerBtn { background-color: #fee2e2; color: #dc2626; border: none; border-radius: 8px; font-weight: bold; padding: 10px; }
#DangerBtn:hover { background-color: #fca5a5; }
QCheckBox { font-family: "Microsoft YaHei UI"; font-size: 13px; color: #374151; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #d1d5db; background-color: #ffffff; }
QCheckBox::indicator:checked { background-color: #3b82f6; border-color: #3b82f6; }
QGraphicsView { border: none; background-color: #e5e7eb; border-radius: 12px; }
QSlider::groove:horizontal { height: 6px; background: #d1d5db; border-radius: 3px; }
QSlider::handle:horizontal { width: 16px; height: 16px; background: #3b82f6; border-radius: 8px; margin: -5px 0; }
"""

DARK_THEME = """
QMainWindow, QStackedWidget { background-color: #0d1117; }
#Sidebar { background-color: #161b22; border-right: 1px solid #30363d; }
#Sidebar QPushButton { background-color: transparent; border: none; border-radius: 8px; color: #8b949e; text-align: left; padding: 12px 16px; font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 13px; font-weight: bold; }
#Sidebar QPushButton:hover { background-color: #21262d; color: #c9d1d9; }
#Sidebar QPushButton:checked { background-color: #1f6feb; color: #ffffff; }
#ThemeToggle { background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9; text-align: center; }
#ThemeToggle:hover { background-color: #30363d; }
#Card { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; }
QLabel { color: #c9d1d9; font-family: "Microsoft YaHei UI"; }
QListWidget { background-color: #0d1117; border: 1px solid #30363d; border-radius: 8px; color: #c9d1d9; font-size: 12px; padding: 5px; outline: none; }
QListWidget::item:selected { background-color: #1f6feb; color: #ffffff; border-radius: 4px; }
#ActionBtn { background-color: #238636; border: none; border-radius: 8px; color: #ffffff; font-weight: bold; padding: 12px; font-size: 13px; }
#ActionBtn:hover { background-color: #2ea44f; }
#DangerBtn { background-color: #3b2323; color: #f85149; border: 1px solid #f85149; border-radius: 8px; font-weight: bold; padding: 10px; }
#DangerBtn:hover { background-color: #da3633; color: #ffffff; }
QCheckBox { font-family: "Microsoft YaHei UI"; font-size: 13px; color: #c9d1d9; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 2px solid #484f58; background-color: #161b22; }
QCheckBox::indicator:checked { background-color: #1f6feb; border-color: #1f6feb; }
QGraphicsView { border: none; background-color: #090c10; border-radius: 12px; }
QSlider::groove:horizontal { height: 6px; background: #484f58; border-radius: 3px; }
QSlider::handle:horizontal { width: 16px; height: 16px; background: #1f6feb; border-radius: 8px; margin: -5px 0; }
"""
# =========================================================


# ======================== 可拖拽标记点 ========================
# ======================== 可拖拽标记点 ========================
class DraggableMarker(QGraphicsEllipseItem):
    """可拖拽的地图标记点，带序号+坐标标签。
    拖拽释放后通过 callback 通知 MapCanvasStudio（QGraphicsEllipseItem
    不是 QObject，无法使用 pyqtSignal，改用函数回调）。
    """
    def __init__(self, index, x, y, on_drag_finished=None, parent=None):
        r = 12
        super().__init__(x - r, y - r, r * 2, r * 2, parent)
        self.index = index
        self._radius = r
        self._drag_start = (x, y)
        self._was_dragged = False
        self._on_drag_finished = on_drag_finished  # callback(obj)

        # 外观
        self.setBrush(QBrush(QColor(249, 115, 22)))   # 橙色
        self.setPen(QPen(QColor(255, 255, 255), 2.5))
        self.setZValue(10)

        # 可移动 + 可选中 + 发送位置变化
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges, True)

        # 标签文字: "1: (123, 432)"
        self.label = QGraphicsSimpleTextItem(self)
        self.label.setZValue(11)
        self.label.setBrush(QBrush(QColor(255, 255, 255)))
        font = self.label.font()
        font.setPointSize(9)
        font.setBold(True)
        self.label.setFont(font)
        self._update_label_pos()
        self.update_label()

    def update_label(self):
        cx = self.rect().x() + self.rect().width() // 2 + self.pos().x()
        cy = self.rect().y() + self.rect().height() // 2 + self.pos().y()
        self.label.setText(f"{self.index}: ({int(cx)},{int(cy)})")
        self._update_label_pos()

    def _update_label_pos(self):
        r = self._radius
        self.label.setPos(self.pos().x() + r + 4,
                          self.pos().y() + r - 8)

    def set_index(self, idx):
        self.index = idx
        self.update_label()

    def get_center(self):
        r = self._radius
        return (self.rect().x() + r + self.pos().x(),
                self.rect().y() + r + self.pos().y())

    def set_on_drag_finished(self, cb):
        """设置拖拽完成后的回调函数 callback(marker_obj)"""
        self._on_drag_finished = cb

    def itemChange(self, change, value):
        if change == QGraphicsEllipseItem.ItemPositionHasChanged:
            self.update_label()
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        self._drag_start = self.get_center()
        self._was_dragged = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self._was_dragged = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        new_pos = self.get_center()
        dx = abs(new_pos[0] - self._drag_start[0])
        dy = abs(new_pos[1] - self._drag_start[1])
        if (dx > 2 or dy > 2) and self._on_drag_finished is not None:
            self._on_drag_finished(self)

    def remove_from_scene(self):
        if self.scene():
            try:
                if self.label in self.scene().items():
                    self.scene().removeItem(self.label)
            except Exception:
                pass
            try:
                if self in self.scene().items():
                    self.scene().removeItem(self)
            except Exception:
                pass
class MapCanvasStudio(QGraphicsView):
    point_added_signal = pyqtSignal(float, float, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.map_item = None
        self.markers = []
        self._player_markers = []
        self._route_items = []
        self._zoom = 0
        self._edit_mode = False  # True=单击添加标记模式
        self._marker_count = 0  # 已添加标记计数
        self._draggable_markers = []  # DraggableMarker 列表
        self._confirm_pending = False  # 是否有待确认的拖拽
        self._last_dragged_idx = -1


    def set_edit_mode(self, enabled):
        """切换编辑模式：True=单击添加标记点"""
        self._edit_mode = enabled
        if enabled:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def set_confirm_visible(self):
        """拖拽后弹出确认对话框"""
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "确认拖拽",
            "标记位置已改变，是否重新生成路线？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self._rebuild_route()

    def _rebuild_route(self):
        """根据 DraggableMarker 当前位置重绘路线连线"""
        pts = [m.get_center() for m in self._draggable_markers]
        # 清除旧路线
        for item in self._route_items:
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self._route_items.clear()
        # 重绘
        if len(pts) > 1:
            pen = QPen(QColor(59, 130, 246), 3, Qt.DashLine)
            for i in range(len(pts) - 1):
                x1, y1 = pts[i]
                x2, y2 = pts[i+1]
                line = self.scene.addLine(x1, y1, x2, y2, pen)
                self._route_items.append(line)
        # 更新序号标签
        for i, m in enumerate(self._draggable_markers):
            m.set_index(i + 1)
            m.update_label()
        self._marker_count = len(self._draggable_markers)


    def set_map_pixmap(self, pixmap):
        self.scene.clear()
        self.markers.clear()
        self._player_markers.clear()
        self._route_items.clear()
        for m in self._draggable_markers:
            m.remove_from_scene()
        self._draggable_markers.clear()
        self._marker_count = 0
        self.map_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.map_item)
        self.setSceneRect(self.map_item.boundingRect())

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 0.85
        if event.angleDelta().y() > 0 and self._zoom < 12:
            self._zoom += 1
            self.scale(factor, factor)
        elif event.angleDelta().y() < 0 and self._zoom > -6:
            self._zoom -= 1
            self.scale(factor, factor)

    def mousePressEvent(self, event):
        # 编辑模式：单击添加标记点
        if self._edit_mode and event.button() == Qt.LeftButton and self.map_item:
            scene_pos = self.mapToScene(event.pos())
            if self.map_item.boundingRect().contains(scene_pos):
                x, y = scene_pos.x(), scene_pos.y()
                self._marker_count += 1
                idx = self._marker_count
                marker = DraggableMarker(idx, x, y)
                self.scene.addItem(marker)
                self._draggable_markers.append(marker)
                # 连接拖拽完成信号（延迟连接以避免递归）
                marker.set_on_drag_finished(lambda m: self.set_confirm_visible())
                # 重绘路线
                self._rebuild_route()
                # 通知外部（可选）
                self.point_added_signal.emit(x, y, str(idx))
                return
        # 非编辑模式 → 滚动手势
        super().mousePressEvent(event)

    def draw_all_markers(self, points_list):
        # 清除旧的 DraggableMarker
        for m in self._draggable_markers:
            m.remove_from_scene()
        self._draggable_markers.clear()

        # 清除路线
        for item in self._route_items:
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self._route_items.clear()
        for item in self.markers:
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self.markers.clear()

        # 创建新 DraggableMarker
        for i, pt in enumerate(points_list):
            idx = i + 1
            x, y = pt.get('x', pt[0]), pt.get('y', pt[1]) if isinstance(pt, dict) else (pt[0], pt[1])
            marker = DraggableMarker(idx, x, y)
            self.scene.addItem(marker)
            self._draggable_markers.append(marker)
            marker.set_on_drag_finished(lambda m: self.set_confirm_visible())

        # 重绘路线
        self._rebuild_route()
        self._marker_count = len(self._draggable_markers)

    def draw_route(self, path_points):
        """画导航路线（蓝色实线）"""
        for item in self._route_items:
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self._route_items.clear()

        if len(path_points) > 1:
            pen = QPen(QColor(59, 130, 246), 4)
            pen.setCosmetic(True)
            for i in range(len(path_points) - 1):
                x1, y1 = path_points[i]
                x2, y2 = path_points[i+1]
                line = self.scene.addLine(x1, y1, x2, y2, pen)
                self._route_items.append(line)

    def set_player_position(self, x, y):
        """在地图上标记玩家当前位置（准星 + 坐标文字）"""
        self.clear_player_marker()
        pen = QPen(QColor(0, 255, 100, 200), 2)
        pen.setCosmetic(True)
        s = 20
        line_h = self.scene.addLine(x - s, y, x + s, y, pen)
        line_v = self.scene.addLine(x, y - s, x, y + s, pen)
        self._player_markers.extend([line_h, line_v])
        circle = self.scene.addEllipse(x - 15, y - 15, 30, 30, pen)
        self._player_markers.append(circle)
        txt = QGraphicsSimpleTextItem(f"({int(x)},{int(y)})")
        txt.setBrush(QBrush(QColor(0, 255, 100)))
        txt.setPos(x + 20, y - 10)
        self.scene.addItem(txt)
        self._player_markers.append(txt)

    def update_player_transform(self, x, y, angle, conf):
        """实时渲染玩家位置箭头并动态旋转"""
        if not hasattr(self, 'player_marker') or self.player_marker is None:
            # 创建一个类似原神/洛克王国的玩家导航三角箭头
            arrow_poly = QPolygonF([QPointF(0, -18), QPointF(-12, 12), QPointF(0, 6), QPointF(12, 12)])
            self.player_marker = QGraphicsPolygonItem(arrow_poly)
            self.player_marker.setBrush(QBrush(QColor(0, 255, 255, 230)))  # 高亮青色
            self.player_marker.setPen(QPen(QColor(255, 255, 255), 2))
            self.player_marker.setZValue(9999)  # 确保箭头永远在最上层
            self.scene.addItem(self.player_marker)
            
        # 更新坐标与旋转
        self.player_marker.setPos(x, y)
        self.player_marker.setRotation(angle)
        
        # 仅当置信度 > 10% 时，将大图视野中心平滑移动到玩家位置
        if conf > 10.0:
            self.centerOn(x, y)

    def clear_player_marker(self):
        """清除玩家位置标记"""
        for item in self._player_markers:
            try:
                if item.scene() == self.scene:
                    self.scene.removeItem(item)
            except Exception:
                pass
        self._player_markers = []


class ControlPanel(QMainWindow):
    def __init__(self, overlay):
        super().__init__()
        self.overlay = overlay
        self.setWindowTitle("Roco Go! (ok-ww UI Edition)")
        self.resize(1150, 750)
        self.is_light_mode = True

        # 视觉追踪
        self._vision_tracking = False
        self._capture_engine = CaptureEngine()
        self._vision_matcher = VisionMatcher(self._capture_engine)
        self._vision_matcher.position_updated.connect(self._on_vision_position)
        self._vision_matcher.match_status.connect(self._on_match_status)

        # 新 VisionEngine (纯视觉追踪，独立线程)
        self._vision_engine = VisionEngine(big_map_path=str(DEFAULT_MAP_PATH))
        self._vision_engine.position_updated.connect(self._on_vision_engine_position)
        self._vision_timer = QTimer()
        self._vision_timer.timeout.connect(self._vision_timer_tick)

        self._last_vision_result = None
        self._last_frame = None
        self._current_route = None  # 当前导航路线
        self._match_threshold = 50   # 特征匹配置信度阈值

        self.points_database = []
        self.load_local_points_json()
        self.init_modern_layout()
        self.apply_current_theme()
        self.sync_and_refresh_data()

    # ── 布局初始化 ────────────────────────────────────────
    def init_modern_layout(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        global_layout = QHBoxLayout(main_widget)
        global_layout.setContentsMargins(0, 0, 0, 0)
        global_layout.setSpacing(0)

        # 侧边栏
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setObjectName("Sidebar")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(15, 30, 15, 20)
        sb_layout.setSpacing(10)

        title = QLabel("ROCO MAP")
        title.setFont(QFont("Segoe UI Black", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #3b82f6; margin-bottom: 20px;")
        sb_layout.addWidget(title)

        self.btn_map = QPushButton("🗺 航点与地图工作室")
        self.btn_map.setCheckable(True)
        self.btn_map.setChecked(True)

        self.btn_set = QPushButton("⚙️ 导航与雷达设置")
        self.btn_set.setCheckable(True)

        sb_layout.addWidget(self.btn_map)
        sb_layout.addWidget(self.btn_set)
        sb_layout.addStretch()

        self.btn_theme = QPushButton("🌞 切换为暗色模式")
        self.btn_theme.setObjectName("ThemeToggle")
        self.btn_theme.clicked.connect(self.toggle_theme)
        sb_layout.addWidget(self.btn_theme)

        # 视觉追踪开关
        self.btn_vision = QPushButton("📸 视觉追踪 [关]")
        self.btn_vision.setCheckable(True)
        self.btn_vision.setChecked(False)
        self.btn_vision.clicked.connect(self._toggle_vision_tracking)
        sb_layout.addWidget(self.btn_vision)

        self.status_label = QLabel("🔴 未识别到游戏窗口")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setWordWrap(True)
        self.status_label.setMaximumHeight(60)
        sb_layout.addWidget(self.status_label)

        # 主卡片区
        self.page_stack = QStackedWidget()
        self.btn_map.clicked.connect(lambda: self.switch_tab(0))
        self.btn_set.clicked.connect(lambda: self.switch_tab(1))

        self.setup_map_studio_page()
        self.setup_settings_page()

        global_layout.addWidget(sidebar)
        global_layout.addWidget(self.page_stack)

    def switch_tab(self, index):
        self.page_stack.setCurrentIndex(index)
        self.btn_map.setChecked(index == 0)
        self.btn_set.setChecked(index == 1)

    def toggle_theme(self):
        self.is_light_mode = not self.is_light_mode
        self.apply_current_theme()
        self.btn_theme.setText("🌞 切换为暗色模式" if self.is_light_mode else "🌙 切换为亮色模式")

    def apply_current_theme(self):
        theme_qss = LIGHT_THEME if self.is_light_mode else DARK_THEME
        self.setStyleSheet(theme_qss)

    # ── 地图工作室页面（T5 导航功能在这里）────────────────────
    def setup_map_studio_page(self):
        page = QWidget()
        lay = QHBoxLayout(page)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(20)

        # 左侧面板
        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)

        # 导航操作卡片
        nav_card = QFrame()
        nav_card.setObjectName("Card")
        nav_lay = QVBoxLayout(nav_card)
        nav_lay.setContentsMargins(20, 20, 20, 20)
        nav_lay.setSpacing(12)

        nav_title = QLabel("🧭 导航操作")
        nav_title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        nav_lay.addWidget(nav_title)

        self.btn_set_target = QPushButton("🎯 设为目标航点")
        self.btn_set_target.setObjectName("ActionBtn")
        self.btn_set_target.clicked.connect(self._set_nav_target)
        nav_lay.addWidget(self.btn_set_target)

        self.btn_start_nav = QPushButton("🚀 开始导航")
        self.btn_start_nav.setObjectName("ActionBtn")
        self.btn_start_nav.clicked.connect(self._start_navigation)
        nav_lay.addWidget(self.btn_start_nav)

        self.btn_clear_route = QPushButton("🗑 清除路线")
        self.btn_clear_route.setObjectName("DangerBtn")
        self.btn_clear_route.clicked.connect(self._clear_route)
        nav_lay.addWidget(self.btn_clear_route)

        self.route_info_label = QLabel("路线信息：未规划")
        self.route_info_label.setWordWrap(True)
        self.route_info_label.setStyleSheet("padding: 8px; background: rgba(59,130,246,0.1); border-radius: 6px;")
        nav_lay.addWidget(self.route_info_label)

        left_panel.addWidget(nav_card)

        # 数据管理卡片（Feature 5: JSON 导入/导出）
        data_card = QFrame()
        data_card.setObjectName("Card")
        dat_lay = QVBoxLayout(data_card)
        dat_lay.setContentsMargins(20, 20, 20, 20)
        dat_lay.setSpacing(10)

        dat_title = QLabel("💾 路线数据")
        dat_title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        dat_lay.addWidget(dat_title)

        self.btn_export_json = QPushButton("📥 导出路线 JSON")
        self.btn_export_json.setObjectName("ActionBtn")
        self.btn_export_json.clicked.connect(self._export_route_json)
        dat_lay.addWidget(self.btn_export_json)

        self.btn_import_json = QPushButton("📤 导入路线 JSON")
        self.btn_import_json.setObjectName("ActionBtn")
        self.btn_import_json.clicked.connect(self._import_route_json)
        dat_lay.addWidget(self.btn_import_json)

        # Feature 6: 图片标点导入
        self.btn_import_image = QPushButton("📷 导入图片自动标点")
        self.btn_import_image.setObjectName("ActionBtn")
        self.btn_import_image.clicked.connect(self._import_image_points)
        dat_lay.addWidget(self.btn_import_image)

        # 编辑模式切换
        self.btn_edit_mode = QPushButton("✏️ 编辑模式 [关]")
        self.btn_edit_mode.setCheckable(True)
        self.btn_edit_mode.setChecked(False)
        self.btn_edit_mode.setStyleSheet(
            "QPushButton { background: #f9fafb; border: 1px solid #e5e7eb; color: #6b7280; "
            "text-align: center; padding: 8px 12px; border-radius: 8px; font-size: 12px; }"
            "QPushButton:checked { background: #fef3c7; border-color: #f59e0b; color: #92400e; }"
            "QPushButton:hover { background: #f3f4f6; }"
        )
        self.btn_edit_mode.clicked.connect(self._toggle_edit_mode)
        dat_lay.addWidget(self.btn_edit_mode)

        left_panel.addWidget(data_card)
        left_panel.addStretch()

        # 右侧地图画布
        self.studio_canvas = MapCanvasStudio()
        map_pixmap = QPixmap(str(DEFAULT_MAP_PATH))
        if map_pixmap.isNull():
            # 降级到金字塔
            zoom_path = PROJECT_ROOT / "assets" / "maps" / "pyramid" / "zoom_0.5.png"
            if zoom_path.exists():
                map_pixmap = QPixmap(str(zoom_path))
        if not map_pixmap.isNull():
            self.studio_canvas.set_map_pixmap(map_pixmap.scaled(
                2048, 2048, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

        lay.addLayout(left_panel)
        lay.addWidget(self.studio_canvas, 1)
        self.page_stack.addWidget(page)

    # ── T5 导航功能方法 ────────────────────────────────────
    def _set_nav_target(self):
        """设为目标航点"""
        if self._last_vision_result is None:
            QMessageBox.warning(self, "警告", "请先开启视觉追踪获取当前位置！")
            return
        px, py = self._last_vision_result[0], self._last_vision_result[1]
        name, ok = QInputDialog.getText(self, "设为目标", f"当前位置: ({int(px)}, {int(py)})\n请输入目标名称（可选，直接回车使用最近点位）:")
        self._nav_target_name = name.strip() if ok else ""
        self.status_label.setText(f"🎯 目标已设定: {self._nav_target_name or '最近点位'}")

    def _start_navigation(self):
        """开始导航：调用 PathFinder 计算路线"""
        if self._last_vision_result is None:
            QMessageBox.warning(self, "警告", "请先开启视觉追踪获取当前位置！")
            return
        try:
            from path_finder import PathFinder
            finder = PathFinder()
            px, py = self._last_vision_result[0], self._last_vision_result[1]

            # 如果有指定目标名称，查找目标坐标
            if hasattr(self, '_nav_target_name') and self._nav_target_name:
                from coord_aligner import CoordAligner
                aligner = CoordAligner()
                result = aligner.find_nearest(px, py)
                if result:
                    tx, ty = result['x'], result['y']
                else:
                    QMessageBox.warning(self, "警告", "未找到附近点位！")
                    return
            else:
                # 默认导航到最近点位
                from coord_aligner import CoordAligner
                aligner = CoordAligner()
                result = aligner.find_nearest(px, py)
                if result:
                    tx, ty = result['x'], result['y']
                else:
                    QMessageBox.warning(self, "警告", "未找到附近点位！")
                    return

            path = finder.a_star(int(px), int(py), int(tx), int(ty))
            if path is None:
                self.route_info_label.setText("路线信息：未找到可达路线")
                return

            self._current_route = path
            # 显示路线到 MapCanvasStudio
            if hasattr(self, 'studio_canvas'):
                self.studio_canvas.draw_route(path)
            # 显示路线到 OverlayUI
            if self.overlay and hasattr(self.overlay, 'set_route'):
                self.overlay.set_route(path)
            dist = len(path)
            self.route_info_label.setText(f"路线信息：{dist} 步 | 目标: ({int(tx)}, {int(ty)})")
            self.status_label.setText(f"🚀 导航中 → 目标 ({int(tx)}, {int(ty)})")
        except Exception as e:
            QMessageBox.warning(self, "导航错误", str(e))

    def _clear_route(self):
        """清除当前路线"""
        self._current_route = None
        if hasattr(self, 'studio_canvas'):
            self.studio_canvas.draw_route([])
        if self.overlay and hasattr(self.overlay, 'set_route'):
            self.overlay.set_route([])
        self.route_info_label.setText("路线信息：未规划")
        self.status_label.setText("🗑 路线已清除")

    # ── Feature 5: JSON 导入/导出 ──────────────────────────
    def _export_route_json(self):
        """导出当前航点+路线到用户选择的 JSON 文件"""
        path, _ = QFileDialog.getSaveFileName(
            self, "导出路线 JSON", str(PROJECT_ROOT / "routes" / "route_export.json"),
            "JSON Files (*.json)"
        )
        if not path:
            return
        data = {
            "points": self.points_database,
            "route": self._current_route if self._current_route else [],
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "导出成功", f"已保存到: {path}")

    def _import_route_json(self):
        """从 JSON 文件导入航点路线"""
        path, _ = QFileDialog.getOpenFileName(
            self, "导入路线 JSON", str(PROJECT_ROOT / "routes"),
            "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            imported = data.get("points", [])
            if not imported:
                QMessageBox.warning(self, "警告", "JSON 中无有效航点数据！")
                return
            # 合并到当前数据库
            self.points_database = imported
            self._current_route = data.get("route", None)
            # 重新绘制
            if hasattr(self, 'studio_canvas') and self._current_route:
                self.studio_canvas.draw_route(self._current_route)
                route_len = len(self._current_route)
                self.route_info_label.setText(f"路线信息：{route_len} 步 (已导入)")
            # 重绘标记
            if hasattr(self, 'studio_canvas'):
                self.studio_canvas.draw_all_markers(self.points_database)
            self.save_local_points_json()
            QMessageBox.information(self, "导入成功", f"已导入 {len(imported)} 个航点")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    # ── Feature 6: 图片标点自动识别 ─────────────────────────
    def _import_image_points(self):
        """导入图片，自动检测标点，预览确认"""
        path, _ = QFileDialog.getOpenFileName(
            self, "导入标点图片", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        try:
            detector = PointDetector(min_area=20, max_area=8000, min_circularity=0.4)
            points = detector.detect(path)
            if not points:
                QMessageBox.information(self, "检测结果", "图片中未检测到标记点，请确认图片包含彩色圆点标记。")
                return
            # 生成预览图并显示确认对话框
            preview_bgr = detector.generate_preview(path, points)
            h, w, _ = preview_bgr.shape
            # BGR -> RGB -> QPixmap
            rgb = preview_bgr[:, :, [2, 1, 0]]
            qimg = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)

            # 弹出确认对话框
            dlg = QDialog(self)
            dlg.setWindowTitle(f"检测到 {len(points)} 个标点 — 预览确认")
            dlg.setMinimumSize(800, 600)
            layout = QVBoxLayout(dlg)

            # 滚动预览区
            scroll = QScrollArea()
            label = QLabel()
            label.setPixmap(pixmap.scaled(
                780, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
            label.setAlignment(Qt.AlignCenter)
            scroll.setWidget(label)
            layout.addWidget(scroll)

            # 操作按钮
            btn_layout = QHBoxLayout()
            btn_ok = QPushButton("✅ 确认导入")
            btn_ok.setObjectName("ActionBtn")
            btn_ok.clicked.connect(dlg.accept)
            btn_cancel = QPushButton("❌ 取消")
            btn_cancel.setObjectName("DangerBtn")
            btn_cancel.clicked.connect(dlg.reject)
            btn_layout.addStretch()
            btn_layout.addWidget(btn_cancel)
            btn_layout.addWidget(btn_ok)
            layout.addLayout(btn_layout)

            dlg.setStyleSheet(self.styleSheet())
            if dlg.exec_() == QDialog.Accepted:
                # 将检测到的点转为航点
                self.points_database = []
                for pt in points:
                    self.points_database.append({
                        "name": str(len(self.points_database) + 1),
                        "x": pt["x"],
                        "y": pt["y"],
                    })
                self.save_local_points_json()
                if hasattr(self, 'studio_canvas'):
                    self.studio_canvas.draw_all_markers(self.points_database)
                self.route_info_label.setText(f"路线信息：已导入 {len(points)} 个标点")
                QMessageBox.information(self, "导入成功",
                    f"已导入 {len(points)} 个标点（编号 1-{len(points)}）。\n"
                    f"可在航点与地图工作室页面手动调整顺序。")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    # ── 编辑模式切换 ────────────────────────────────────
    def _toggle_edit_mode(self, checked):
        """切换编辑模式"""
        if hasattr(self, "studio_canvas") and self.studio_canvas:
            self.studio_canvas.set_edit_mode(checked)
        if checked:
            self.btn_edit_mode.setText("✏️ 编辑模式 [开]")
            self.status_label.setText("🟠 编辑模式：在大地图上单击添加标记点")
        else:
            self.btn_edit_mode.setText("✏️ 编辑模式 [关]")
            self.status_label.setText("📋 浏览模式：滚轮缩放 / 拖拽平移")

    # ── 设置页面（T6 增强）────────────────────────────────
    def setup_settings_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(20)

        # 滚动区容器
        scroll_content = QWidget()
        scroll_lay = QVBoxLayout(scroll_content)
        scroll_lay.setSpacing(20)

        # 雷达控制卡片
        card = QFrame()
        card.setObjectName("Card")
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(25, 25, 25, 25)
        c_lay.setSpacing(25)

        self.cb_show = QCheckBox("显示置顶雷达 HUD (图1样式圆盘)")
        self.cb_show.setChecked(True)
        self.cb_show.stateChanged.connect(
            lambda s: self.overlay.show() if s == Qt.Checked else self.overlay.hide()
        )
        c_lay.addWidget(self.cb_show)

        self.cb_pen = QCheckBox("开启雷达鼠标穿透 (点击雷达直接操作底层游戏)")
        self.cb_pen.stateChanged.connect(self._toggle_penetration)
        c_lay.addWidget(self.cb_pen)

        lay.addWidget(card)

        # T6 新增：截图控制卡片
        capture_card = QFrame()
        capture_card.setObjectName("Card")
        cap_lay = QVBoxLayout(capture_card)
        cap_lay.setContentsMargins(25, 25, 25, 25)
        cap_lay.setSpacing(20)

        cap_title = QLabel("📷 截图控制")
        cap_title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        cap_lay.addWidget(cap_title)

        self.btn_reselect_roi = QPushButton("🔄 重新框选小地图区域")
        self.btn_reselect_roi.setObjectName("ActionBtn")
        self.btn_reselect_roi.clicked.connect(self._reselect_roi)
        cap_lay.addWidget(self.btn_reselect_roi)

        # 截图间隔滑块
        interval_lay = QHBoxLayout()
        interval_lay.addWidget(QLabel("截图间隔:"))
        self.slider_interval = QSlider(Qt.Horizontal)
        self.slider_interval.setRange(100, 2000)
        self.slider_interval.setValue(500)
        self.slider_interval.valueChanged.connect(self._on_interval_changed)
        interval_lay.addWidget(self.slider_interval, 1)
        self.label_interval = QLabel("500ms")
        interval_lay.addWidget(self.label_interval)
        cap_lay.addLayout(interval_lay)

        # 匹配阈值滑块
        threshold_lay = QHBoxLayout()
        threshold_lay.addWidget(QLabel("匹配阈值:"))
        self.slider_threshold = QSlider(Qt.Horizontal)
        self.slider_threshold.setRange(10, 100)
        self.slider_threshold.setValue(50)
        self.slider_threshold.valueChanged.connect(self._on_threshold_changed)
        threshold_lay.addWidget(self.slider_threshold, 1)
        self.label_threshold = QLabel("50%")
        threshold_lay.addWidget(self.label_threshold)
        cap_lay.addLayout(threshold_lay)

        lay.addWidget(capture_card)

        # T6 新增：截图预览卡片
        preview_card = QFrame()
        preview_card.setObjectName("Card")
        prev_lay = QVBoxLayout(preview_card)
        prev_lay.setContentsMargins(25, 25, 25, 25)
        prev_lay.setSpacing(15)

        prev_title = QLabel("🖼 截图预览")
        prev_title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        prev_lay.addWidget(prev_title)

        self.preview_label = QLabel("等待截图...")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(320, 180)
        self.preview_label.setStyleSheet("background: #111; border-radius: 8px; color: #888;")
        prev_lay.addWidget(self.preview_label)
        lay.addWidget(preview_card)

        lay.addStretch()
        self.page_stack.addWidget(page)

        # 预览定时器
        self._preview_timer = QTimer()
        self._preview_timer.timeout.connect(self._update_preview)
        self._preview_timer.start(200)

    # ── T6 设置页槽函数 ────────────────────────────────────
    def _toggle_penetration(self, state):
        """切换雷达鼠标穿透"""
        if self.overlay and hasattr(self.overlay, "set_penetration"):
            self.overlay.set_penetration(state == Qt.Checked)

    def _reselect_roi(self):
        """重新框选小地图区域 (ROISelector 可视化框选)"""
        self._roi_selector = ROISelector()
        self._roi_selector.roi_selected.connect(self._on_roi_selected)
        self._roi_selector.show()
        # 选择器是模态的，信号异步返回

    def _on_roi_selected(self, x, y, w, h):
        """ROISelector 选区完成回调"""
        roi_dict = {"top": y, "left": x, "width": w, "height": h}
        self._vision_engine.set_roi(x, y, w, h)
        QMessageBox.information(self, "选区成功", f"ROI: x={x}, y={y}, {w}x{h}")
        self.status_label.setText(f"✅ 小地图区域已更新 ({w}x{h})")

    def _on_interval_changed(self, value):
        self.label_interval.setText(f"{value}ms")
        self._capture_engine.set_interval(value)
        if hasattr(self, "_vision_engine"):
            self._vision_engine.set_delay(value)

    def _on_threshold_changed(self, value):
        self.label_threshold.setText(f"{value}%")
        self._match_threshold = value

    def _update_preview(self):
        """更新截图预览"""
        if not hasattr(self, 'preview_label'):
            return
        frame = self._vision_matcher.get_last_frame()
        if frame is not None:
            try:
                h, w, c = frame.shape
                if c == 3:
                    qimg = QImage(frame.data, w, h, w * 3, QImage.Format_RGB888)
                else:
                    qimg = QImage(frame.data, w, h, w * 4, QImage.Format_RGBA8888)
                pixmap = QPixmap.fromImage(qimg).scaled(
                    320, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(pixmap)
            except Exception:
                pass

    # ── 视觉追踪控制 ────────────────────────────────
    def _toggle_vision_tracking(self, checked):
        """切换视觉追踪开关"""
        self._vision_tracking = checked
        if checked:
            roi = self._capture_engine.get_current_roi()
            if roi is None:
                self.status_label.setText("🟡 请框选游戏窗口区域...")
                roi = self._capture_engine.select_roi()
                if roi is None:
                    self.btn_vision.setChecked(False)
                    self.status_label.setText("🔴 未选择 ROI，追踪取消")
                    return
            ok = self._capture_engine.start_capture()
            if ok:
                self.btn_vision.setText("📸 视觉追踪 [开]")
                self.status_label.setText("🟡 追踪启动中...")
                self._vision_timer.start(500)
            else:
                self.btn_vision.setChecked(False)
                self.status_label.setText("🔴 截图引擎启动失败")
        else:
            try:
                self._capture_engine.stop_capture()
                self._vision_matcher.shutdown()
            except Exception:
                pass
            self.btn_vision.setText("📸 视觉追踪 [关]")
            self._vision_timer.stop()
            self.status_label.setText("🔴 追踪已关闭")
            # 停止 VisionEngine
            if hasattr(self, "_vision_engine") and self._vision_engine.isRunning():
                self._vision_engine.stop()

    def _on_vision_position(self, map_x, map_y, confidence, heading):
        """VisionMatcher.position_updated 信号回调"""
        self._last_vision_result = (map_x, map_y, heading, confidence)

    def _on_vision_engine_position(self, map_x, map_y, angle, confidence):
        """VisionEngine.position_updated 信号回调 (新引擎)"""
        self._last_vision_result = (map_x, map_y, angle, confidence)
        icon = "🟢" if confidence >= 0.5 else "🟡"
        self.status_label.setText(
            f"{icon} VisionEngine  x={int(map_x)}  y={int(map_y)}  "
            f"θ={angle:.0f}°  conf={confidence:.0%}"
        )
        # 更新大地图玩家位置（黄色标记 + 旋转箭头）
        if hasattr(self, "studio_canvas"):
            self.studio_canvas.set_player_position(map_x, map_y)
            self.studio_canvas.update_player_transform(map_x, map_y, angle, confidence)
        # 更新 Overlay HUD（红色区域指针旋转）
        if self.overlay and hasattr(self.overlay, "set_player_angle"):
            self.overlay.set_player_angle(angle)
        elif self.overlay and hasattr(self.overlay, "update_player_pos"):
            self.overlay.update_player_pos(map_x, map_y, angle)

    def _on_match_status(self, status):
        """VisionMatcher.match_status 信号回调"""
        pass

    def _vision_timer_tick(self):
        """定时器回调：轮询 VisionMatcher 结果并更新 UI"""
        result = self._vision_matcher.get_last_position()
        self._last_vision_result = result

        if result is None:
            self.status_label.setText("🟡 特征匹配中...")
            return

        x, y, conf = result[:3]
        icon = "🟢" if conf >= (self._match_threshold / 100.0) else "🟡"
        self.status_label.setText(
            f"{icon} 已定位  x={int(x)}  y={int(y)}  conf={conf:.0%}"
        )

        if hasattr(self, "studio_canvas"):
            self.studio_canvas.set_player_position(x, y)

    # ── 数据联动逻辑 ────────────────────────────────────
    def handle_add_point(self, x, y, name):
        self.points_database.append({"name": name, "x": x, "y": y})

    def sync_and_refresh_data(self):
        pass  # TODO: 刷新列表显示

    def load_local_points_json(self):
        try:
            if CONFIG_PATH.exists():
                with open(str(CONFIG_PATH), 'r', encoding='utf-8') as f:
                    self.points_database = json.load(f)
        except Exception:
            self.points_database = []

    def save_local_points_json(self):
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(str(CONFIG_PATH), 'w', encoding='utf-8') as f:
                json.dump(self.points_database, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def clear_points(self):
        """清除所有航点并同步到磁盘"""
        self.points_database.clear()
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(str(CONFIG_PATH), 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        self.sync_and_refresh_data()
        self._clear_route()
