# src/roi_selector.py
from PyQt5.QtWidgets import QWidget, QApplication, QRubberBand
from PyQt5.QtCore import Qt, QRect, pyqtSignal
from PyQt5.QtGui import QColor, QPalette

class ROISelector(QWidget):
    """全屏半透明遮罩选区工具"""
    roi_selected = pyqtSignal(int, int, int, int) # x, y, w, h

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.setGeometry(QApplication.desktop().geometry())
        
        # 黑色半透明背景
        self.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
        
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self.origin = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.rubber_band.setGeometry(QRect(self.origin, self.origin))
            self.rubber_band.show()

    def mouseMoveEvent(self, event):
        if not self.origin: return
        self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            rect = self.rubber_band.geometry()
            self.rubber_band.hide()
            self.close()
            # 发射选区坐标 (左, 上, 宽, 高)
            self.roi_selected.emit(rect.x(), rect.y(), rect.width(), rect.height())