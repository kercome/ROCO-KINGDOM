#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
overlay_ui.py — PyQt5 纯净版半透明叠加窗口

Features:
1. Clean radar minimap overlay with no extra text panels
2. Edge resizing and full-window dragging support
3. Minimum size limit: 2.5cm x 2.5cm (96x96 px at 96 DPI)
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsSimpleTextItem
)
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import (
    QPixmap, QColor, QPen, QBrush, QFont, QRegion, QPainterPath
)
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
MAP_WIDTH = 4096
MAP_HEIGHT = 4096
RESIZE_MARGIN = 12  # 窗口边缘可拖拽缩放的热区宽度（px）


class OverlayUI(QMainWindow):
    """半透明叠加窗口，纯净小地图模式"""

    def __init__(self, workspace_path=None):
        super().__init__()
        self.workspace_path = Path(workspace_path) if workspace_path else PROJECT_ROOT / "assets" / "maps"
        self._sim_x = MAP_WIDTH // 2
        self._sim_y = MAP_HEIGHT // 2
        self._route_path = None  
        self._player_angle = 0.0   # VisionEngine 传入的面朝角度

        self.init_modules()
        self.init_ui()
        self.init_timer()
        self.init_window_follower()

    # ── 模块初始化 ──────────────────────────────────────────
    def init_modules(self):
        # CoordAligner
        try:
            from coord_aligner import CoordAligner
            self.aligner = CoordAligner()
        except Exception:
            self.aligner = None

        # PathFinder
        try:
            from path_finder import PathFinder
            self.finder = PathFinder()
        except Exception:
            self.finder = None

        # VisionEngine
        try:
            from vision_engine import VisionEngine
            self.vision = VisionEngine()
        except Exception:
            self.vision = None

        self.minimap_pixmap = self._load_minimap_image()
        self._follow_enabled = True
        self._penetration_enabled = False
        self._route_points = []       # 导航路线点列表
        self._route_lines = []        # QGraphicsLineItem 列表

    def _load_minimap_image(self):
        """加载缩略图，适应各种缩放尺寸"""
        zoom_quarter = os.path.join(self.workspace_path, "pyramid", "zoom_0.25.png")
        zoom_half = os.path.join(self.workspace_path, "pyramid", "zoom_0.5.png")
        main_map = r"D:\roco_hd_world_map.v3.jpg"

        if os.path.exists(zoom_quarter):
            return QPixmap(zoom_quarter)
        elif os.path.exists(zoom_half):
            return QPixmap(zoom_half).scaled(1024, 1024, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        elif os.path.exists(main_map):
            return QPixmap(main_map).scaled(1024, 1024, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return QPixmap()

    # ── UI 构建 (纯净地图模式) ─────────────────────────────────
    def init_ui(self):
        self.setWindowTitle("Roco Navigator HUD")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        
        # 物理限制：约 2.5cm x 2.5cm (96 DPI下为 96x96像素)
        self.setMinimumSize(96, 96)  

        central = QWidget()
        # 科技感暗色半透明圆角底板
        central.setStyleSheet("background: rgba(20, 20, 20, 180); border-radius: 16px;")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8) 

        # 小地图 View
        self.minimap_view = QGraphicsView()
        self.minimap_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.minimap_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.minimap_view.setStyleSheet("border: 1px solid #444; background: #111; border-radius: 12px;")
        self.scene = QGraphicsScene()
        self.minimap_view.setScene(self.scene)
        
        # 将事件拦截器绑定到view，以便实现全屏拖拽
        self.minimap_view.viewport().installEventFilter(self)

        layout.addWidget(self.minimap_view)
        self.setCentralWidget(central)
        
        self.resize(260, 260)  # 默认初始大小
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, 60)

        self._apply_rounded_mask()

    # ── 圆角掩码与自适应 ───────────────────────────────────
    def _apply_rounded_mask(self):
        """动态圆角矩形掩码"""
        w, h = self.width(), self.height()
        corner_radius = 16
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), corner_radius, corner_radius)
        mask_region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(mask_region)

    def set_penetration(self, enabled):
        """开启/关闭鼠标穿透 - True 则点击穿过 HUD 到达底层"""
        self._penetration_enabled = enabled
        self.setAttribute(Qt.WA_TransparentForMouseEvents, enabled)

        # 刷新导航路线
        if self._route_points:
            self._draw_route_on_scene()

    def set_route(self, path_points):
        """接收导航路线点列表，在 HUD 小地图上画蓝色路线"""
        self._route_points = path_points if path_points else []
        self._draw_route_on_scene()

    def set_player_angle(self, angle_deg):
        """VisionEngine 传入的玩家面朝角度（度），触发重绘时指针旋转"""
        self._player_angle = angle_deg % 360.0

    def _draw_route_on_scene(self):
        """在 QGraphicsScene 上绘制导航路线（蓝色折线）"""
        if not hasattr(self, '_route_items'):
            self._route_items = []
        for item in self._route_items:
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self._route_items = []
        if len(self._route_points) < 2:
            return
        pen = QPen(QColor(59, 130, 246), 3)
        pen.setCosmetic(True)
        for i in range(len(self._route_points) - 1):
            g1 = self._route_points[i]
            g2 = self._route_points[i + 1]
            p1 = self._global_to_minimap(g1)
            p2 = self._global_to_minimap(g2)
            line = self.scene.addLine(p1[0], p1[1], p2[0], p2[1], pen)
            self._route_items.append(line)

    def _global_to_minimap(self, global_pt):
        """将 4096x4096 全局坐标映射到 HUD 小地图坐标"""
        view_w = max(self.minimap_view.width(), 1)
        view_h = max(self.minimap_view.height(), 1)
        scale_x = view_w / 4096.0
        scale_y = view_h / 4096.0
        return (int(global_pt[0] * scale_x), int(global_pt[1] * scale_y))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_rounded_mask()
        # 尺寸变化时，地图自适应缩放铺满框体
        if self.scene.sceneRect().isValid():
            self.minimap_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    # ── 自由拖动 & 边缘缩放 ──────────────────────────────
    def _hit_test(self, pos):
        """检测鼠标位置用于拖拽与缩放判定"""
        x, y, w, h = pos.x(), pos.y(), self.width(), self.height()
        m = RESIZE_MARGIN
        top, bottom = y < m, y > h - m
        left, right = x < m, x > w - m
        if top and left:     return 'topleft'
        if top and right:    return 'topright'
        if bottom and left:  return 'bottomleft'
        if bottom and right: return 'bottomright'
        if top:              return 'top'
        if bottom:           return 'bottom'
        if left:             return 'left'
        if right:            return 'right'
        return 'client' 

    def eventFilter(self, obj, event):
        """拦截 View 上的鼠标事件，实现拖动和缩放"""
        if obj == self.minimap_view.viewport():
            if event.type() == event.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self._drag_hit = self._hit_test(self.mapFromGlobal(event.globalPos()))
                    if self._drag_hit != 'client':
                        self._start_native_resize(event.globalPos())
                    else:
                        self._start_native_drag(event.globalPos())
                    return True
                elif event.button() == Qt.RightButton:
                    # 右键保留模拟寻路功能
                    scene_pt = self.minimap_view.mapToScene(event.pos())
                    ratio = 4096.0 / max(1, self.minimap_pixmap.width())
                    self._sim_x = int(scene_pt.x() * ratio)
                    self._sim_y = int(scene_pt.y() * ratio)
                    self.start_navigation((self._sim_x, self._sim_y))
                    return True
            elif event.type() == event.MouseMove:
                ht = self._hit_test(self.mapFromGlobal(event.globalPos()))
                cursors = {
                    'topleft': Qt.SizeFDiagCursor, 'bottomright': Qt.SizeFDiagCursor,
                    'topright': Qt.SizeBDiagCursor, 'bottomleft': Qt.SizeBDiagCursor,
                    'top': Qt.SizeVerCursor, 'bottom': Qt.SizeVerCursor,
                    'left': Qt.SizeHorCursor, 'right': Qt.SizeHorCursor,
                }
                self.minimap_view.viewport().setCursor(cursors.get(ht, Qt.OpenHandCursor))
        return super().eventFilter(obj, event)

    def _start_native_drag(self, globalPos):
        try:
            import win32gui, win32con
            hwnd = int(self.winId())
            win32gui.ReleaseCapture()
            win32gui.PostMessage(hwnd, win32con.WM_NCLBUTTONDOWN, win32con.HTCAPTION, 0)
        except ImportError: pass

    def _start_native_resize(self, globalPos):
        try:
            import win32gui, win32con
            hwnd = int(self.winId())
            ht_map = {
                'left': win32con.HTLEFT, 'right': win32con.HTRIGHT,
                'top': win32con.HTTOP, 'bottom': win32con.HTBOTTOM,
                'topleft': win32con.HTTOPLEFT, 'topright': win32con.HTTOPRIGHT,
                'bottomleft': win32con.HTBOTTOMLEFT, 'bottomright': win32con.HTBOTTOMRIGHT,
            }
            ht_code = ht_map.get(getattr(self, '_drag_hit', 'bottomright'), win32con.HTBOTTOMRIGHT)
            win32gui.ReleaseCapture()
            win32gui.PostMessage(hwnd, win32con.WM_NCLBUTTONDOWN, ht_code, 0)
        except ImportError: pass

    # ── 业务逻辑更新 ─────────────────────────────────────────
    def init_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(200)

    def update_display(self):
        px, py = self._get_player_position()
        nearest_info = self._query_nearest(px, py)
        self.draw_minimap(px, py, nearest_info)

    def draw_minimap(self, px, py, nearest_info):
        self.scene.clear()
        
        # 渲染底图并设置场景范围
        if not self.minimap_pixmap.isNull():
            self.scene.addPixmap(self.minimap_pixmap)
            if self.scene.sceneRect().isEmpty():
                self.scene.setSceneRect(self.minimap_pixmap.rect().toRectF())
                self.minimap_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

        # 动态比例尺
        ratio = max(1, self.minimap_pixmap.width()) / 4096.0
        mp_x = px * ratio
        mp_y = py * ratio

        # 玩家红点定位
        outer = QGraphicsEllipseItem(mp_x - 6, mp_y - 6, 12, 12)
        outer.setPen(QPen(QColor(255, 60, 60, 220), 1.5))
        outer.setBrush(QBrush(QColor(255, 40, 40, 180)))
        self.scene.addItem(outer)

        inner = QGraphicsEllipseItem(mp_x - 2, mp_y - 2, 4, 4)
        inner.setPen(QPen(Qt.NoPen)) # ✅ 已在此处修复 TypeError Bug
        inner.setBrush(QBrush(QColor(255, 255, 255, 220)))
        self.scene.addItem(inner)

        # 方向指针三角（随玩家朝向旋转）
        import math
        tip_len = 14
        tip_r = 5
        rad = math.radians(self._player_angle)
        tip_x = mp_x + tip_len * math.cos(rad)
        tip_y = mp_y - tip_len * math.sin(rad)
        left_x = mp_x + tip_r * math.cos(rad + 2.4)
        left_y = mp_y - tip_r * math.sin(rad + 2.4)
        right_x = mp_x + tip_r * math.cos(rad - 2.4)
        right_y = mp_y - tip_r * math.sin(rad - 2.4)
        from PyQt5.QtGui import QPolygonF
        from PyQt5.QtCore import QPointF
        arrow = self.scene.addPolygon(
            QPolygonF([QPointF(tip_x, tip_y), QPointF(left_x, left_y), QPointF(right_x, right_y)]),
            QPen(QColor(255, 200, 50, 255), 1.5),
            QBrush(QColor(255, 200, 50, 200))
        )

        # 路线绘制
        if self._route_path and len(self._route_path) >= 2:
            pen = QPen(QColor(100, 255, 100, 180), 2)
            for i in range(len(self._route_path) - 1):
                x1, y1 = self._route_path[i]
                x2, y2 = self._route_path[i + 1]
                line = QGraphicsLineItem(x1 * ratio, y1 * ratio, x2 * ratio, y2 * ratio)
                line.setPen(pen)
                self.scene.addItem(line)

    def _get_player_position(self):
        if self.vision is not None:
            try:
                x, y, theta, conf = self.vision.get_current_position()
                return x, y
            except Exception: pass
        return self._sim_x, self._sim_y

    def _query_nearest(self, px, py):
        if self.aligner is None: return None
        try:
            results = self.aligner.find_nearest(px, py, count=1)
            if results:
                item = results[0]
                pt = item[0] if isinstance(item, (list, tuple)) else item
                return {"name": str(pt.get("title") or pt.get("name") or pt.get("id", "Unknown"))}
        except Exception: pass
        return None

    def start_navigation(self, target_point):
        if self.finder is None: return
        try:
            px, py = self._get_player_position()
            tx, ty = target_point[0], target_point[1]
            res = self.finder.a_star(px, py, tx, ty)
            self._route_path = res["path"] if res else None
        except Exception: pass

    # ── 窗口跟随与穿透逻辑保持不变 ────────────────────────────
    def init_window_follower(self):
        try:
            import win32gui
            self._follow_timer = QTimer()
            self._follow_timer.timeout.connect(self._follow_game_window)
            self._follow_timer.start(100)
            self._last_game_rect = None
        except ImportError: pass

    def _follow_game_window(self):
        try:
            import win32gui
            _game_hwnd = None
            for title in ["洛克王国：世界", "洛克王国"]:
                hwnd = win32gui.FindWindow(None, title)
                if hwnd:
                    _game_hwnd = hwnd
                    break
            
            if not _game_hwnd:
                def enum_cb(hwnd, results):
                    if not win32gui.IsWindowVisible(hwnd): return
                    text = win32gui.GetWindowText(hwnd)
                    if any(ex in text for ex in ["Navigator", "Studio", "VS Code", "PowerShell", "Roco Go"]): return
                    if "洛克王国：世界" in text or "洛克王国" in text: results.append(hwnd)
                results = []
                win32gui.EnumWindows(enum_cb, results)
                if results: _game_hwnd = results[0]

            if _game_hwnd:
                rect = win32gui.GetWindowRect(_game_hwnd)
                if rect != self._last_game_rect:
                    self._last_game_rect = rect
                    self.move(rect[2] - self.width() - 5, rect[1] + 5)
        except ImportError: pass

    def set_click_through(self, enabled):
        try:
            import win32gui, win32con
            hwnd = int(self.winId())
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if enabled: style |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
            else: style &= ~(win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
        except ImportError: pass