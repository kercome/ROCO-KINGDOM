"""
capture_engine.py - 自定义截屏选区 + mss 高频截图引擎
依赖: PyQt5, mss, numpy, pygetwindow
"""
import numpy as np
from pathlib import Path
from PyQt5.QtCore import (
    QObject, QThread, pyqtSignal, Qt,
    QMutex, QMutexLocker, QEventLoop
)
from PyQt5.QtWidgets import QWidget, QRubberBand, QApplication, QMessageBox
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPixmap
import mss
import json

CONFIG_PATH = Path(r"D:\github\Roco\data\capture_config.json")


class ROISelector(QWidget):
    """全屏半透明 ROI 选区遮罩窗口。"""
    def __init__(self):
        super().__init__()
        self._origin = None
        self._rubber = None
        self._result = None
        self._loop = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        if self._rubber is not None:
            rect = self._rubber.geometry()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(0, 200, 255), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._origin = event.globalPos()
            self._rubber = QRubberBand(QRubberBand.Rectangle, self)
            self._rubber.setGeometry(event.x(), event.y(), 0, 0)
            self._rubber.show()
            self.update()

    def mouseMoveEvent(self, event):
        if self._origin is not None and self._rubber is not None:
            rect = QRect(self._origin, event.globalPos()).normalized()
            self._rubber.setGeometry(rect)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._rubber is not None:
            rect = self._rubber.geometry()
            self._result = (rect.x(), rect.y(), rect.width(), rect.height())
            self.close()
            if self._loop is not None:
                self._loop.quit()

    def select(self):
        """阻塞式调用，返回 (x, y, w, h) 或 None。"""
        self.show()
        self._loop = QEventLoop()
        self._loop.exec_()
        if self._result and self._result[2] >= 10 and self._result[3] >= 10:
            return self._result
        return None


class _CaptureWorker(QThread):
    """截图工作线程，持有 CaptureEngine 引用。"""
    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    def run(self):
        self.engine._capture_loop()


class CaptureEngine(QObject):
    """
    自定义截屏选区 + mss 高频截图引擎。
    信号链: frame_captured(np.ndarray) -> VisionMatcher.on_frame
    """
    frame_captured = pyqtSignal(np.ndarray)       # 每帧 RGB 数组
    roi_changed    = pyqtSignal(int, int, int, int)  # (x, y, w, h)
    status_changed = pyqtSignal(str)               # 'idle' / 'capturing' / 'stopped'

    def __init__(self, parent=None):
        super().__init__(parent)
        self._roi = None          # (x, y, w, h) or None
        self._interval_ms = 500
        self._running = False
        self._worker = None
        self._load_config()

    # ---- 公开 API ----

    def auto_detect_game_window(self):
        """自动检测洛克王国世界窗口，返回右上角小地图 ROI (x, y, w, h) 或 None。"""
        try:
            import pygetwindow as gw
        except ImportError:
            return None

        candidates = gw.getWindowsWithTitle("洛克王国")
        if not candidates:
            candidates = gw.getWindowsWithTitle("Roco")
        if not candidates:
            return None

        win = candidates[0]
        if not win.isActive:
            try:
                win.restore()
            except Exception:
                pass

        # 小地图通常在游戏窗口右上角，约占窗口宽 1/5、高 1/4
        map_w = max(180, int(win.width * 0.22))
        map_h = max(180, int(win.height * 0.28))
        map_x = win.left + win.width - map_w - 8   # 右边缘内缩 8px
        map_y = win.top + 8                                # 顶部内缩 8px

        return (map_x, map_y, map_w, map_h)

    def select_roi(self):
        """先尝试自动检测游戏窗口小地图，失败则手动框选。阻塞直到完成。"""
        roi = self.auto_detect_game_window()
        if roi is not None:
            self._roi = roi
            self.roi_changed.emit(*roi)
            self._save_config()
            QMessageBox.information(
                None, "自动检测成功",
                f"已自动定位游戏小地图区域：\n"
                f"x={roi[0]}, y={roi[1]}, w={roi[2]}, h={roi[3]}"
            )
            return roi

        # 回退到手动框选
        selector = ROISelector()
        result = selector.select()
        selector.deleteLater()
        if result is not None:
            self._roi = result
            self.roi_changed.emit(*result)
            self._save_config()
            return result
        return None

    def get_current_roi(self):
        return self._roi

    def set_roi(self, x, y, w, h):
        self._roi = (x, y, w, h)
        self.roi_changed.emit(x, y, w, h)
        self._save_config()

    def set_interval(self, ms):
        ms = max(100, min(5000, int(ms)))
        self._interval_ms = ms
        self._save_config()

    def get_interval(self):
        return self._interval_ms

    def start_capture(self):
        """启动截图线程，成功返回 True。"""
        if self._roi is None:
            self.status_changed.emit('no_roi')
            return False
        if self._running:
            return True
        self._running = True
        self._worker = _CaptureWorker(self)
        self._worker.start()
        self.status_changed.emit('capturing')
        return True

    def stop_capture(self):
        self._running = False
        if self._worker is not None:
            self._worker.wait(3000)
            self._worker = None
        self.status_changed.emit('stopped')

    def is_running(self):
        return self._running

    # ---- 内部方法 ----

    def _capture_loop(self):
        """在 QThread 中执行，循环截图并 emit frame_captured。"""
        x, y, w, h = self._roi
        roi_dict = {'left': x, 'top': y, 'width': w, 'height': h}
        sct = mss.mss()
        try:
            while self._running:
                shot = sct.grab(roi_dict)
                # shot.raw 是 BGRA bytes，shape=(h, w, 4)
                bgra = np.frombuffer(shot.raw, dtype=np.uint8).reshape(h, w, 4)
                rgb = bgra[:, :, [2, 1, 0]]   # BGRA -> RGB
                self.frame_captured.emit(rgb)
                QThread.msleep(self._interval_ms)
        finally:
            sct.close()

    def _save_config(self):
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            cfg = {
                'roi': list(self._roi) if self._roi else None,
                'interval_ms': self._interval_ms
            }
            CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False),
                                  encoding='utf-8')
        except Exception:
            pass

    def _load_config(self):
        try:
            if CONFIG_PATH.exists():
                cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
                if cfg.get('roi'):
                    self._roi = tuple(cfg['roi'])
                self._interval_ms = max(100, min(5000, cfg.get('interval_ms', 500)))
        except Exception:
            pass
