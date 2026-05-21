"""
vision_engine.py
游戏窗口截取与视觉匹配引擎 - Roco Navigation Tool

功能：
  1. 检测洛克王国游戏窗口
  2. 高速截取游戏画面 (mss)
  3. ORB 特征匹配定位玩家位置
  4. 卡尔曼滤波平滑轨迹
  5. 估算玩家朝向角度

依赖：
  - pygetwindow: 窗口检测
  - mss: 高速屏幕截取
  - OpenCV (cv2): ORB 特征匹配、Homography、Kalman Filter
  - NumPy: 数组运算
  - PIL: 图像格式转换
  - coord_mapper: 加载总底图
"""

import time
import numpy as np
import cv2
import mss
import pygetwindow as gw
from PIL import Image
import os

# ── 常量 ────────────────────────────────────────────────────
ORB_FEATURES = 2000
MIN_MATCH_COUNT = 10
RANSAC_THRESHOLD = 5.0
KALMAN_PROCESS_NOISE = 1e-3
KALMAN_MEASUREMENT_NOISE = 1e-2


class VisionEngine:
    """
    视觉引擎：封装窗口检测、屏幕截取、特征匹配、定位、滤波
    """

    def __init__(self, window_title_keywords=None):
        """
        初始化视觉引擎

        Args:
            window_title_keywords: 游戏窗口标题关键词列表，默认 ["洛克王国", "Roco"]
        """
        if window_title_keywords is None:
            window_title_keywords = ["洛克王国"]

        self.window_title_keywords = window_title_keywords
        self.game_window = None
        self.window_hwnd = None
        self.window_rect = None  # (left, top, width, height)

        self.mss_instance = None
        self.orb = None
        self.flann = None
        self.kalman = None
        self.kalman_initialized = False

        self.reference_map = None  # 总底图 (OpenCV BGR)
        self.reference_map_gray = None
        self.reference_keypoints = None
        self.reference_descriptors = None

        self.last_position = None
        self.last_theta = None
        self.confidence = 0.0

        self._init_orb()
        self._init_kalman()
        self._load_reference_map()

    def _init_orb(self):
        """初始化 ORB 特征检测器和 FLANN 匹配器"""
        print("[VisionEngine] 初始化 ORB 特征检测器...")
        self.orb = cv2.ORB_create(nfeatures=ORB_FEATURES)
        # FLANN 参数 for ORB
        FLANN_INDEX_LSH = 6
        index_params = dict(
            algorithm=FLANN_INDEX_LSH,
            table_number=6,
            key_size=12,
            multi_probe_level=1
        )
        search_params = dict(checks=50)
        self.flann = cv2.FlannBasedMatcher(index_params, search_params)
        print("[VisionEngine] ORB 初始化完成")

    def _init_kalman(self):
        """初始化卡尔曼滤波器"""
        print("[VisionEngine] 初始化卡尔曼滤波器...")
        self.kalman = cv2.KalmanFilter(4, 2)
        # 状态向量: [x, y, dx, dy]
        # 测量向量: [x, y]

        # 转移矩阵 A (状态转移)
        self.kalman.transitionMatrix = np.array([
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        # 测量矩阵 H
        self.kalman.measurementMatrix = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=np.float32)

        # 过程噪声协方差
        self.kalman.processNoiseCov = np.eye(4, dtype=np.float32) * KALMAN_PROCESS_NOISE

        # 测量噪声协方差
        self.kalman.measurementNoiseCov = np.eye(2, dtype=np.float32) * KALMAN_MEASUREMENT_NOISE

        # 后验误差协方差
        self.kalman.errorCovPost = np.eye(4, dtype=np.float32)

        # 后验状态估计 (初始化为0)
        self.kalman.statePost = np.zeros((4, 1), dtype=np.float32)

        self.kalman_initialized = False
        print("[VisionEngine] 卡尔曼滤波器初始化完成")

    def _load_reference_map(self, zoom=1.0):
        """
        加载总底图并预计算 ORB 特征

        Args:
            zoom: 金字塔缩放等级
        """
        print(f"[VisionEngine] 加载总底图 (zoom={zoom})...")
        try:
            from coord_mapper import load_map

            pil_img = load_map(zoom=zoom)
            # PIL Image -> OpenCV BGR
            if pil_img.mode == "RGBA":
                pil_img = pil_img.convert("RGB")
            rgb = np.array(pil_img)
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            self.reference_map = bgr
            self.reference_map_gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

            # 预计算特征点和描述子
            print("[VisionEngine] 计算总底图 ORB 特征 (可能需要几秒)...")
            self.reference_keypoints, self.reference_descriptors = self.orb.detectAndCompute(
                self.reference_map_gray, None
            )
            print(f"[VisionEngine] 总底图特征点数量: {len(self.reference_keypoints)}")

        except Exception as e:
            print(f"[VisionEngine] 加载总底图失败: {e}")
            raise

    def detect_game_window(self):
        """
        检测游戏窗口

        Returns:
            bool: 是否成功找到游戏窗口
        """
        print("[VisionEngine] 检测游戏窗口...")
        all_windows = gw.getAllWindows()
        print(f"[VisionEngine] 当前所有窗口 ({len(all_windows)} 个):")
        for w in all_windows[:20]:  # 只打印前20个
            if w.title:
                print(f"  - [{w._hWnd}] {w.title}")

        target_window = None
        for w in all_windows:
            if not w.title:
                continue
            for keyword in self.window_title_keywords:
                if keyword in w.title:
                    target_window = w
                    break
            if target_window:
                break

        if target_window is None:
            print("[VisionEngine] 未找到游戏窗口 (包含 '洛克王国')")
            self.game_window = None
            self.window_hwnd = None
            self.window_rect = None
            return False

        self.game_window = target_window
        self.window_hwnd = target_window._hWnd
        self.window_rect = (
            target_window.left,
            target_window.top,
            target_window.width,
            target_window.height
        )
        print(f"[VisionEngine] 找到游戏窗口: '{target_window.title}'")
        print(f"[VisionEngine] HWND: {self.window_hwnd}")
        print(f"[VisionEngine] 位置: left={self.window_rect[0]}, top={self.window_rect[1]}, "
              f"width={self.window_rect[2]}, height={self.window_rect[3]}")
        return True

    def capture_window(self):
        """
        截取游戏窗口画面

        Returns:
            numpy.ndarray or None: BGR 格式的图像，失败返回 None
        """
        if self.game_window is None:
            if not self.detect_game_window():
                return None

        if self.mss_instance is None:
            self.mss_instance = mss.mss()

        left, top, width, height = self.window_rect

        # 验证窗口尺寸
        if width <= 0 or height <= 0:
            print("[VisionEngine] 窗口尺寸异常，重新检测...")
            if not self.detect_game_window():
                return None
            left, top, width, height = self.window_rect

        # mss 截取区域
        monitor = {
            "top": top,
            "left": left,
            "width": width,
            "height": height
        }

        try:
            start_time = time.time()
            screenshot = np.array(self.mss_instance.grab(monitor))
            elapsed = time.time() - start_time
            fps_estimate = 1.0 / elapsed if elapsed > 0 else 0
            print(f"[VisionEngine] 截取一帧耗时: {elapsed*1000:.2f} ms (预估 FPS: {fps_estimate:.1f})")

            # mss 返回 BGRA (4通道)，转为 BGR (3通道)
            bgr = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
            return bgr

        except Exception as e:
            print(f"[VisionEngine] 截取画面失败: {e}")
            return None

    def match_position(self, frame_bgr):
        """
        将游戏画面与总底图进行 ORB 特征匹配，计算玩家位置

        Args:
            frame_bgr: 游戏画面对应的 BGR 图像

        Returns:
            tuple or None: (x, y, theta, confidence) 或 None (匹配失败)
        """
        if self.reference_descriptors is None:
            print("[VisionEngine] 总底图特征未计算，无法匹配")
            return None

        # 游戏画面转灰度
        frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

        # 计算游戏画面 ORB 特征
        kp_frame, des_frame = self.orb.detectAndCompute(frame_gray, None)
        if des_frame is None or len(kp_frame) < MIN_MATCH_COUNT:
            print(f"[VisionEngine] 游戏画面特征点不足: {len(kp_frame) if kp_frame else 0}")
            return None

        # FLANN 匹配
        matches = self.flann.knnMatch(self.reference_descriptors, des_frame, k=2)

        # Lowe's ratio test
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)

        print(f"[VisionEngine] 良好匹配点数量: {len(good_matches)} (最低要求: {MIN_MATCH_COUNT})")

        if len(good_matches) < MIN_MATCH_COUNT:
            return None

        # 提取匹配点坐标
        src_pts = np.float32([self.reference_keypoints[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp_frame[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        # 计算 Homography (使用 RANSAC 过滤异常值)
        H, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, RANSAC_THRESHOLD)
        if H is None:
            print("[VisionEngine] Homography 计算失败")
            return None

        # 统计内点数量 (用于置信度)
        inlier_count = int(np.sum(mask)) if mask is not None else 0
        confidence = inlier_count / len(good_matches) if len(good_matches) > 0 else 0
        print(f"[VisionEngine] Homography 内点数量: {inlier_count}/{len(good_matches)} (置信度: {confidence:.2%})")

        # 从 Homography 反推游戏画面中心在总底图中的位置
        frame_h, frame_w = frame_bgr.shape[:2]
        center_dst = np.array([[[frame_w / 2, frame_h / 2]]], dtype=np.float32)
        center_src = cv2.perspectiveTransform(center_dst, H)
        x, y = center_src[0][0]

        # 从 Homography 提取旋转角度 (theta)
        # H = [[a, b, c],
        #      [d, e, f],
        #      [g, h, i]]
        # 忽略透视分量，用 a, b, d, e 估算旋转
        a, b = H[0, 0], H[0, 1]
        d, e = H[1, 0], H[1, 1]
        theta_rad = np.arctan2(d, a)  # 从旋转矩阵提取角度
        theta_deg = np.degrees(theta_rad) % 360
        # 0度 = 正北 (图像坐标系 Y轴向下，需要转换)
        theta = (90 - theta_deg) % 360

        print(f"[VisionEngine] 定位结果: x={x:.1f}, y={y:.1f}, theta={theta:.1f}°, 置信度={confidence:.2%}")

        return x, y, theta, confidence

    def smooth_position(self, x, y):
        """
        使用卡尔曼滤波平滑位置

        Args:
            x, y: 当前测量位置

        Returns:
            tuple: (x_smooth, y_smooth) 平滑后的位置
        """
        measurement = np.array([[np.float32(x)], [np.float32(y)]])

        if not self.kalman_initialized:
            # 第一次测量，初始化状态
            self.kalman.statePost = np.array([[x], [y], [0], [0]], dtype=np.float32)
            self.kalman_initialized = True
            prediction = self.kalman.predict()
            self.kalman.correct(measurement)
            return x, y

        # 预测
        prediction = self.kalman.predict()
        # 校正
        corrected = self.kalman.correct(measurement)

        x_smooth = corrected[0, 0]
        y_smooth = corrected[1, 0]

        return x_smooth, y_smooth

    def get_current_position(self):
        """
        获取当前玩家位置 (主接口)

        Returns:
            tuple or None: (x, y, theta, confidence) 或 None (失败)
        """
        # 步骤1: 截取游戏画面
        frame = self.capture_window()
        if frame is None:
            print("[VisionEngine] 截取画面失败，无法定位")
            return None

        # 步骤2: ORB 特征匹配定位
        result = self.match_position(frame)
        if result is None:
            print("[VisionEngine] 特征匹配定位失败")
            return None

        x, y, theta, confidence = result

        # 步骤3: 卡尔曼滤波平滑
        x_smooth, y_smooth = self.smooth_position(x, y)

        print(f"[VisionEngine] 最终结果: x={x_smooth:.1f}, y={y_smooth:.1f}, "
              f"theta={theta:.1f}°, 置信度={confidence:.2%}")

        return x_smooth, y_smooth, theta, confidence

    def shutdown(self):
        """
        释放资源
        """
        print("[VisionEngine] 释放资源...")
        if self.mss_instance is not None:
            self.mss_instance.close()
            self.mss_instance = None
        print("[VisionEngine] 资源释放完成")


# ── 主入口 ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Vision Engine - 定位测试")
    print("=" * 60)

    engine = VisionEngine()

    try:
        # 检测游戏窗口
        if not engine.detect_game_window():
            print("\n[测试结果] 游戏窗口未运行")
            print("[测试结果] 代码编写完成，但无法执行定位测试")
            exit_code = 0  # 不作为失败
        else:
            # 执行一轮定位测试
            print("\n[测试] 执行定位...")
            result = engine.get_current_position()

            if result is None:
                print("\n[测试结果] 定位失败 (可能是特征匹配不通过)")
            else:
                x, y, theta, conf = result
                print(f"\n[测试结果] 定位成功!")
                print(f"  坐标: ({x:.1f}, {y:.1f})")
                print(f"  朝向: {theta:.1f}°")
                print(f"  置信度: {conf:.2%}")

    except Exception as e:
        print(f"\n[测试结果] 发生异常: {e}")
        import traceback
        traceback.print_exc()

    finally:
        engine.shutdown()
        print("\n[测试完成]")
