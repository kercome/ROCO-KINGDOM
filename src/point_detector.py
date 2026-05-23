# -*- coding: utf-8 -*-
"""
point_detector.py - 图片标点自动识别引擎
从地图截图中检测彩色标记点，返回坐标列表。
"""
import cv2
import numpy as np
from pathlib import Path


class PointDetector:
    """检测地图图片中的彩色标记点。"""

    # 常见标记色 HSV 范围（可扩展）
    COLOR_RANGES = {
        "red": [
            (np.array([0, 120, 70]), np.array([10, 255, 255])),
            (np.array([160, 120, 70]), np.array([180, 255, 255])),
        ],
        "orange": [(np.array([10, 100, 100]), np.array([25, 255, 255]))],
        "yellow": [(np.array([25, 80, 100]), np.array([35, 255, 255]))],
        "green": [(np.array([35, 80, 60]), np.array([85, 255, 255]))],
        "blue": [(np.array([90, 80, 60]), np.array([130, 255, 255]))],
        "purple": [(np.array([130, 60, 60]), np.array([160, 255, 255]))],
    }

    def __init__(self, blur_ksize=5, min_area=30, max_area=3000, min_circularity=0.5):
        self.blur_ksize = blur_ksize
        self.min_area = min_area
        self.max_area = max_area
        self.min_circularity = min_circularity

    def detect(self, image_path, colors=None):
        """
        检测图片中的标记点。

        Args:
            image_path: 图片路径 (str/Path)
            colors: 要检测的颜色列表，默认全部 ["red","orange","yellow","green","blue","purple"]

        Returns:
            list of dict: [{"x": float, "y": float, "color": str, "radius": float}, ...]
        """
        src = cv2.imread(str(image_path))
        if src is None:
            raise FileNotFoundError(f"无法读取图片: {image_path}")
        h, w = src.shape[:2]
        hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)

        if colors is None:
            colors = list(self.COLOR_RANGES.keys())

        all_points = []
        for cname in colors:
            for lower, upper in self.COLOR_RANGES.get(cname, []):
                mask = cv2.inRange(hsv, lower, upper)
                # 形态学去噪
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area < self.min_area or area > self.max_area:
                        continue
                    perimeter = cv2.arcLength(cnt, True)
                    circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                    if circularity < self.min_circularity:
                        continue
                    M = cv2.moments(cnt)
                    if M["m00"] == 0:
                        continue
                    cx = M["m10"] / M["m00"]
                    cy = M["m01"] / M["m00"]
                    _, radius = cv2.minEnclosingCircle(cnt)
                    all_points.append({"x": cx, "y": cy, "color": cname, "radius": radius, "w": w, "h": h})

        # 去重（距离 < 10px 的视为同一点，保留 radius 大的）
        if all_points:
            all_points = self._deduplicate(all_points, dist_thresh=10.0)

        # 排序：先按 y 分组（行），再按 x 排序（左→右）
        all_points.sort(key=lambda p: (round(p["y"] / 30) * 30, p["x"]))

        return all_points

    def _deduplicate(self, points, dist_thresh=10.0):
        """合并距离 < dist_thresh 的重复检测点。"""
        points = sorted(points, key=lambda p: p["radius"], reverse=True)
        kept = []
        used = [False] * len(points)
        for i, p in enumerate(points):
            if used[i]:
                continue
            kept.append(p)
            for j in range(i + 1, len(points)):
                if used[j]:
                    continue
                d = np.sqrt((p["x"] - points[j]["x"]) ** 2 + (p["y"] - points[j]["y"]) ** 2)
                if d < dist_thresh:
                    used[j] = True
        return kept

    def generate_preview(self, image_path, points, output_path=None):
        """
        在图片上绘制检测点预览（带编号和坐标）。

        Args:
            image_path: 原图路径
            points: detect() 返回的点列表
            output_path: 输出路径，None 则覆盖原图

        Returns:
            numpy.ndarray: BGR 预览图
        """
        img = cv2.imread(str(image_path))
        if img is None:
            raise FileNotFoundError(f"无法读取图片: {image_path}")

        for i, pt in enumerate(points):
            cx, cy = int(pt["x"]), int(pt["y"])
            r = max(int(pt.get("radius", 15)), 15)
            # 颜色映射
            color_bgr = {"red": (0, 0, 255), "orange": (0, 140, 255),
                         "yellow": (0, 255, 255), "green": (0, 255, 0),
                         "blue": (255, 0, 0), "purple": (255, 0, 255)}.get(pt["color"], (0, 255, 255))

            # 编号圆圈 + 背景
            label = f"{i + 1} ({int(cx)},{int(cy)})"
            cv2.circle(img, (cx, cy), r + 4, color_bgr, 3)
            cv2.circle(img, (cx, cy), 4, (255, 255, 255), -1)

            # 文字背景 + 文字
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            tx, ty = cx + r + 10, cy + th // 2
            cv2.rectangle(img, (tx - 4, ty - th - 4), (tx + tw + 4, ty + 4), (40, 40, 40), -1)
            cv2.putText(img, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # 画连线（按顺序 1→2→3→...）
        for i in range(len(points) - 1):
            p1 = (int(points[i]["x"]), int(points[i]["y"]))
            p2 = (int(points[i + 1]["x"]), int(points[i + 1]["y"]))
            cv2.line(img, p1, p2, (0, 255, 255), 2, cv2.LINE_AA)

        if output_path:
            cv2.imwrite(str(output_path), img)
        return img