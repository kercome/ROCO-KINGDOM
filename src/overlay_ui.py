#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
overlay_ui.py — PyQt5 半透明叠加窗口
实时显示玩家位置、附近点位和导航路线
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsLineItem,
    QGraphicsSimpleTextItem
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import (
    QPixmap, QImage, QPainter, QColor, QPen, QBrush, QFont
)
from PIL import Image


MINIMAP_SIZE = 200
MAP_WIDTH = 4096
MAP_HEIGHT = 4096
SCALE = MINIMAP_SIZE / MAP_WIDTH  # 0.0488


class OverlayUI(QMainWindow):
    """半透明叠加窗口，显示小地图和点位信息"""

    def __init__(self, workspace_path=None):
        super().__init__()
        self.workspace_path = Path(workspace_path) if workspace_path else PROJECT_ROOT / "assets" / "maps"
        self._sim_x = MAP_WIDTH // 2
        self._sim_y = MAP_HEIGHT // 2
        self._frame_count = 0
        self._route_path = None  # 导航路线 [(x,y), ...]

        self.init_modules()
        self.init_ui()
        self.init_timer()
        self.init_window_follower()

    # ── 模块初始化 ──────────────────────────────────────────
    def init_modules(self):
        """延迟导入各引擎模块，失败时优雅降级"""
        print("[OverlayUI] Loading engine modules...")

        # CoordAligner
        try:
            from coord_aligner import CoordAligner
            self.aligner = CoordAligner()
            print("[OverlayUI] CoordAligner loaded OK")
        except Exception as e:
            print(f"[OverlayUI] CoordAligner failed: {e}")
            self.aligner = None

        # PathFinder
        try:
            from path_finder import PathFinder
            self.finder = PathFinder()
            print("[OverlayUI] PathFinder loaded OK")
        except Exception as e:
            print(f"[OverlayUI] PathFinder failed: {e}")
            self.finder = None

        # VisionEngine — 可选，用模拟数据降级
        self.vision = None
        try:
            from vision_engine import VisionEngine
            self.vision = VisionEngine()
            print("[OverlayUI] VisionEngine loaded OK")
        except Exception as e:
            print(f"[OverlayUI] VisionEngine unavailable (simulation mode): {e}")

        # 地图缩略图
        self.minimap_pixmap = self._load_minimap_image()

        # 窗口跟随 / 鼠标穿透 / 坐标显隐 标志位
        self._follow_enabled = True
        self._penetration_enabled = False
        self._show_coords = False

    def _load_minimap_image(self):
        """加载或生成小地图缩略图"""
        zoom_quarter = os.path.join(self.workspace_path, "pyramid", "zoom_0.25.png")
        zoom_half = os.path.join(self.workspace_path, "pyramid", "zoom_0.5.png")

        if os.path.exists(zoom_quarter):
            return QPixmap(zoom_quarter).scaled(
                MINIMAP_SIZE, MINIMAP_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        elif os.path.exists(zoom_half):
            img = Image.open(zoom_half)
            target = int(4096 * 0.25)  # 1024px
            img = img.resize((target, target), Image.LANCZOS)
            temp_path = os.path.join(self.workspace_path, "pyramid", "zoom_0.25_temp.png")
            img.save(temp_path)
            return QPixmap(temp_path).scaled(
                MINIMAP_SIZE, MINIMAP_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        else:
            # 无金字塔图片时返回空pixmap（黑底）
            print("[OverlayUI] WARNING: No pyramid images found, minimap will be blank")
            return QPixmap()

    # ── UI 构建 ─────────────────────────────────────────────
    def init_ui(self):
        self.setWindowTitle("Roco Navigator")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )

        central = QWidget()
        central.setStyleSheet(
            "background: rgba(20, 20, 20, 180); border-radius: 10px;"
        )
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # ── 顶部：小地图 + 信息面板
        top_layout = QHBoxLayout()

        # 小地图
        self.minimap_view = QGraphicsView()
        self.minimap_view.setFixedSize(MINIMAP_SIZE, MINIMAP_SIZE)
        self.minimap_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.minimap_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.minimap_view.setStyleSheet("border: 1px solid #555; background: #111;")
        self.scene = QGraphicsScene()
        self.minimap_view.setScene(self.scene)
        top_layout.addWidget(self.minimap_view)

        # 信息面板
        self.info_panel = QWidget()
        info_layout = QVBoxLayout(self.info_panel)
        info_layout.setContentsMargins(6, 0, 0, 0)
        info_layout.setSpacing(4)

        self.pos_label = QLabel("Position: --")
        self.pos_label.setStyleSheet("color: #ccc; font-size: 11px;")
        self.nearest_label = QLabel("Nearest: --")
        self.nearest_label.setStyleSheet("color: #4fc3f7; font-size: 12px; font-weight: bold;")
        self.dist_label = QLabel("Distance: --")
        self.dist_label.setStyleSheet("color: #81c784; font-size: 11px;")
        self.area_label = QLabel("Area: --")
        self.area_label.setStyleSheet("color: #ffb74d; font-size: 11px;")

        info_layout.addWidget(self.pos_label)
        info_layout.addWidget(self.nearest_label)
        info_layout.addWidget(self.dist_label)
        info_layout.addWidget(self.area_label)
        info_layout.addStretch()
        top_layout.addWidget(self.info_panel)

        # ── 底部状态栏
        self.status_bar = QLabel("Ready | Click minimap to navigate")
        self.status_bar.setStyleSheet("color: #666; font-size: 9px; padding: 2px;")

        layout.addLayout(top_layout)
        layout.addWidget(self.status_bar)
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.resize(420, 260)
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, 60)

    # ── 定时刷新 ────────────────────────────────────────────
    def init_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(200)  # 5 FPS

    # ── 窗口跟随 ──────────────────────────────────────────
    def init_window_follower(self):
        """启动窗口跟随定时器，每 100ms 检测游戏窗口位置"""
        try:
            import win32gui
            _ = win32gui  # verify import
        except ImportError:
            print("[OverlayUI] win32gui not available, window follower disabled")
            self._follow_enabled = False
            return
        self._follow_enabled = True
        self._follow_timer = QTimer()
        self._follow_timer.timeout.connect(self._follow_game_window)
        self._follow_timer.start(100)  # 100ms = 高频跟随
        self._game_hwnd = None
        self._last_game_rect = None

    def _follow_game_window(self):
        """通过 win32gui 检测游戏窗口，自动贴附"""
        try:
            import win32gui, win32con
        except ImportError:
            return
        # 尝试多个窗口标题（按优先级）
        titles = ["洛克王国", "Roco", "TapTap"]
        self._game_hwnd = None
        for title in titles:
            hwnd = win32gui.FindWindow(None, title)
            if hwnd:
                self._game_hwnd = hwnd
                break
        if self._game_hwnd is None:
            # 模糊匹配：遍历所有顶层窗口寻找含关键词的
            def enum_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    text = win32gui.GetWindowText(hwnd)
                    for kw in ["洛克", "Roco", "Chrome_WidgetWin"]:
                        if kw in text:
                            results.append(hwnd)
            results = []
            win32gui.EnumWindows(enum_callback, results)
            if results:
                self._game_hwnd = results[0]
        if self._game_hwnd is None:
            return  # 未找到游戏窗口，保持原位

        rect = win32gui.GetWindowRect(self._game_hwnd)
        gw, gh = rect[2] - rect[0], rect[3] - rect[1]
        # 检查是否变化
        if rect == self._last_game_rect:
            return
        self._last_game_rect = rect
        # 贴附到游戏窗口右上角
        self.move(rect[2] - self.width() - 5, rect[1] + 5)

    # ── 鼠标穿透 ──────────────────────────────────────────
    def set_penetration(self, enabled):
        """设置鼠标穿透：WS_EX_TRANSPARENT + WS_EX_LAYERED"""
        try:
            import win32gui, win32con
        except ImportError:
            print("[OverlayUI] win32gui not available, penetration control disabled")
            return
        hwnd = int(self.winId())
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if enabled:
            style |= win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
            self._penetration_enabled = True
        else:
            style &= ~(win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED)
            self._penetration_enabled = False
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
        # 重绘窗口使样式生效
        win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED)

    # ── 公开控制方法 ──────────────────────────────────────
    def set_topmost(self, enabled):
        """设置绝对置顶"""
        if enabled:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()  # 必须 re-show 使 flags 生效

    def set_show_coords(self, enabled):
        """是否显示坐标文本"""
        self._show_coords = enabled

    # ── 主刷新循环 ──────────────────────────────────────────
    def update_display(self):
        self._frame_count += 1

        # 1. 获取玩家位置
        px, py = self._get_player_position()

        # 2. 查询最近点位
        nearest_info = self._query_nearest(px, py)

        # 3. 更新信息面板
        self.pos_label.setText(f"Position: ({int(px)}, {int(py)})")
        if nearest_info:
            name = nearest_info.get("name", "Unknown")
            dist = nearest_info.get("distance", 0)
            area = nearest_info.get("area", "--")
            self.nearest_label.setText(f"Nearest: {name}")
            self.dist_label.setText(f"Distance: {int(dist)}px")
            self.area_label.setText(f"Area: {area}")
        else:
            self.nearest_label.setText("Nearest: --")
            self.dist_label.setText("Distance: --")
            self.area_label.setText("Area: --")

        # 4. 更新状态栏
        self.status_bar.setText(
            f"Frame {self._frame_count} | ({int(px)}, {int(py)}) | "
            f"Simulation mode"
        )

        # 5. 绘制小地图
        self.draw_minimap(px, py, nearest_info)

    def _get_player_position(self):
        """获取玩家当前位置"""
        if self.vision is not None:
            try:
                x, y, theta, conf = self.vision.get_current_position()
                return x, y
            except Exception:
                pass
        return self._sim_x, self._sim_y

    def _query_nearest(self, px, py):
        """查询最近点位信息"""
        if self.aligner is None:
            return None
        try:
            results = self.aligner.find_nearest(px, py, count=1)
            if not results:
                return None
            # results 可能为 [(point_dict, distance), ...] 或 [dict, ...]
            item = results[0]
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                point_dict, distance = item[0], item[1]
                return {
                    "name": point_dict.get("name", point_dict.get("id", "Unknown")),
                    "distance": distance,
                    "area": point_dict.get("area", "--")
                }
            elif isinstance(item, dict):
                return {
                    "name": item.get("name", item.get("id", "Unknown")),
                    "distance": item.get("distance", 0),
                    "area": item.get("area", "--")
                }
        except Exception as e:
            print(f"[OverlayUI] Query nearest failed: {e}")
        return None

    # ── 小地图绘制 ──────────────────────────────────────────
    def draw_minimap(self, px, py, nearest_info):
        self.scene.clear()

        # 地图底图
        if not self.minimap_pixmap.isNull():
            self.scene.addPixmap(self.minimap_pixmap)

        # 玩家位置：红色圆点
        mp_x = px * SCALE
        mp_y = py * SCALE

        # 红色外圈
        outer = QGraphicsEllipseItem(mp_x - 4, mp_y - 4, 8, 8)
        outer.setPen(QPen(QColor(255, 60, 60, 220), 1.5))
        outer.setBrush(QBrush(QColor(255, 40, 40, 180)))
        self.scene.addItem(outer)

        # 白色内芯
        inner = QGraphicsEllipseItem(mp_x - 2, mp_y - 2, 4, 4)
        inner.setPen(Qt.NoPen)
        inner.setBrush(QBrush(QColor(255, 255, 255, 220)))
        self.scene.addItem(inner)

        # 最近点位：蓝色标记
        if nearest_info:
            np_name = nearest_info.get("name", "")
            label = QGraphicsSimpleTextItem(np_name)
            label.setPen(QPen(QColor(100, 200, 255)))
            label.setFont(QFont("Microsoft YaHei", 7))
            label.setPos(mp_x + 8, mp_y - 6)
            self.scene.addItem(label)

        # 导航路线：绿色线条
        if self._route_path and len(self._route_path) >= 2:
            pen = QPen(QColor(100, 255, 100, 180), 1)
            for i in range(len(self._route_path) - 1):
                x1, y1 = self._route_path[i]
                x2, y2 = self._route_path[i + 1]
                line = QGraphicsLineItem(
                    x1 * SCALE, y1 * SCALE, x2 * SCALE, y2 * SCALE
                )
                line.setPen(pen)
                self.scene.addItem(line)

    # ── 鼠标交互 ────────────────────────────────────────────
    def mousePressEvent(self, event):
        # 判断点击是否在小地图区域内
        pos = self.minimap_view.mapFromGlobal(event.globalPos())
        view_rect = self.minimap_view.rect()
        if pos.x() >= 0 and pos.y() >= 0 and pos.x() <= view_rect.width() and pos.y() <= view_rect.height():
            # 将小地图坐标映射回 4096x4096
            self._sim_x = int(pos.x() / SCALE)
            self._sim_y = int(pos.y() / SCALE)
            self._sim_x = max(0, min(MAP_WIDTH, self._sim_x))
            self._sim_y = max(0, min(MAP_HEIGHT, self._sim_y))
            self.status_bar.setText(
                f"Clicked → ({self._sim_x}, {self._sim_y}) | "
                f"Right-click to navigate"
            )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self._compute_navigation(self._sim_x, self._sim_y)

    # ── 导航计算 ────────────────────────────────────────────
    def start_navigation(self, target_point):
        """启动导航：计算并显示路线"""
        if isinstance(target_point, dict):
            tx = target_point.get("pixel_x", self._sim_x)
            ty = target_point.get("pixel_y", self._sim_y)
        elif isinstance(target_point, (list, tuple)) and len(target_point) >= 2:
            tx, ty = target_point[0], target_point[1]
        else:
            return
        self._compute_navigation(tx, ty)

    def _compute_navigation(self, gx, gy):
        """从当前位置到目标计算路线"""
        if self.finder is None:
            self.status_bar.setText("PathFinder not available")
            return
        px, py = self._get_player_position()
        try:
            result = self.finder.a_star(px, py, gx, gy)
            if result and result.get("path"):
                self._route_path = result["path"]
                dist = result.get("distance", 0)
                self.status_bar.setText(
                    f"Route: {len(result['path'])} steps, {int(dist)}px"
                )
            else:
                self._route_path = None
                self.status_bar.setText("No route found")
        except Exception as e:
            self.status_bar.setText(f"Route error: {e}")


# ═══════════════════════════════════════════════════════════
#  直接运行测试
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OverlayUI()
    window.show()
    print("[OverlayUI] Window shown. Click the minimap to move.")
    sys.exit(app.exec_())