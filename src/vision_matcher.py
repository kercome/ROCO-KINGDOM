"""
vision_matcher.py - ORB 特征匹配 + 局部搜索 + Kalman 防抖
依赖: OpenCV, numpy, PyQt5
"""
import cv2
import numpy as np
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class VisionMatcher(QObject):
    """ORB 特征匹配 + 局部搜索优化，输出地图定位坐标。

    信号链:
      CaptureEngine.frame_captured -> VisionMatcher.on_frame
      VisionMatcher.position_updated -> ControlPanel.update_player_marker
    """

    position_updated = pyqtSignal(float, float, float, float)
    # 参数: map_x(float), map_y(float), confidence(0~1), heading_angle(float)
    match_status = pyqtSignal(str)
    # 值: "initializing" / "tracking" / "lost" / "searching"

    def __init__(self, capture_engine, ref_map_path=None):
        """
        capture_engine: CaptureEngine 实例
        ref_map_path: 参考底图路径，默认 assets/maps/roco_hd_world_map.v3.png
        """
        super().__init__()
        self.cap_eng = capture_engine

        # ---- 加载参考底图 ----
        map_path = ref_map_path or str(
            PROJECT_ROOT / "assets" / "maps" / "roco_hd_world_map.v3.png"
        )
        self.ref_map = self._load_ref_map(map_path)
        print(f"[VisionMatcher] 参考底图加载完成: {self.ref_map.shape}")

        # 转灰度 + CLAHE 增强
        self.ref_gray = cv2.cvtColor(self.ref_map, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self.ref_gray = clahe.apply(self.ref_gray)

        # ORB 特征提取（一次性缓存）
        self.orb = cv2.ORB_create(nfeatures=2000,
                                  scaleFactor=1.2,
                                  nlevels=8,
                                  edgeThreshold=31,
                                  patchSize=31,
                                  fastThreshold=20)
        self.last_frame = None  # 缓存最近一帧用于预览
        self.ref_kp, self.ref_des = self.orb.detectAndCompute(self.ref_gray, None)
        print(f"[VisionMatcher] 参考底图 ORB 特征点: {len(self.ref_kp)}")

        # FLANN LSH 匹配器（ORB 专用）
        FLANN_INDEX_LSH = 6
        index_params = dict(algorithm=FLANN_INDEX_LSH,
                            table_number=6,
                            key_size=12,
                            multi_probe_level=1)
        search_params = dict(checks=50)
        self.flann = cv2.FlannBasedMatcher(index_params, search_params)

        # 跟踪状态
        self.last_px = None
        self.last_py = None
        self.last_conf = 0.0
        self.frames_since_match = 0
        self.lost_count = 0
        self.total_frames = 0

        # Kalman 滤波器
        self._init_kalman()

        # 连接信号
        self.cap_eng.frame_captured.connect(self.on_frame)
        print("[VisionMatcher] 初始化完成，已连接 CaptureEngine.frame_captured")

    # ================================================================
    #  核心匹配
    # ================================================================

    def on_frame(self, frame_rgb: np.ndarray):
        """每帧截图回调"""
        self.total_frames += 1

        # 1. RGB -> BGR -> gray + CLAHE
        frame_bgr = frame_rgb[:, :, ::-1].copy()
        self.last_frame = frame_bgr.copy()  # 缓存用于预览
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # 2. 决定搜索范围
        USE_LOCAL = (
            self.last_px is not None
            and self.last_conf > 0.7
            and self.frames_since_match < 30
        )

        # 3. 当前帧 ORB 特征
        kp2, des2 = self.orb.detectAndCompute(gray, None)
        if des2 is None or len(kp2) < 8:
            self._mark_lost()
            return

        # 4. 匹配
        if USE_LOCAL:
            self._match_local(kp2, des2, gray)
        else:
            self._full_search(kp2, des2)

    def _match_local(self, kp2, des2, gray):
        """局部搜索：在上一帧 ±300px 范围内匹配"""
        x1 = max(0, int(self.last_px) - 300)
        y1 = max(0, int(self.last_py) - 300)
        x2 = min(self.ref_gray.shape[1], int(self.last_px) + 300)
        y2 = min(self.ref_gray.shape[0], int(self.last_py) + 300)

        local_gray = self.ref_gray[y1:y2, x1:x2]
        local_kp, local_des = self.orb.detectAndCompute(local_gray, None)
        if local_des is None or len(local_kp) < 8:
            self._full_search(kp2, des2)
            return

        matches = self.flann.knnMatch(des2, local_des, k=2)
        src_pts, dst_pts = self._lowe_ratio(matches, kp2, local_kp)
        if len(src_pts) < 8:
            self._mark_lost()
            return

        # 局部坐标偏移到全图坐标
        dst_pts = dst_pts + np.float32([[x1, y1]])
        self._compute_position(gray, src_pts, dst_pts)

    def _full_search(self, kp2, des2):
        """全图 ORB 匹配（首次 / 失锁恢复）"""
        matches = self.flann.knnMatch(des2, self.ref_des, k=2)
        src_pts, dst_pts = self._lowe_ratio(matches, kp2, self.ref_kp)
        if len(src_pts) < 8:
            self._mark_lost()
            return
        self._compute_position(
            cv2.cvtColor(cv2.cvtColor(self.ref_gray, cv2.COLOR_GRAY2BGR), cv2.COLOR_BGR2GRAY),
            src_pts, dst_pts
        )

    def _compute_position(self, gray, src_pts, dst_pts):
        """计算单应性矩阵 → 中心点坐标"""
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if M is None:
            self._mark_lost()
            return

        h, w = gray.shape[:2]
        center = np.float32([[[w / 2, h / 2]]])
        map_pt = cv2.perspectiveTransform(center, M)[0][0]
        map_x, map_y = float(map_pt[0]), float(map_pt[1])

        conf = float(mask.sum() / len(mask)) if len(mask) > 0 else 0.0

        # 边界检查
        if map_x < 0 or map_x > self.ref_gray.shape[1] or map_y < 0 or map_y > self.ref_gray.shape[0]:
            self._mark_lost()
            return

        # Kalman 滤波
        kf_x, kf_y = self._kalman_correct(map_x, map_y)
        angle = self._estimate_angle(src_pts, dst_pts)

        self.last_px, self.last_py = kf_x, kf_y
        self.last_conf = conf
        self.frames_since_match = 0
        self.lost_count = 0

        self.match_status.emit("tracking")
        self.position_updated.emit(kf_x, kf_y, conf, angle)

    def _mark_lost(self):
        self.lost_count += 1
        self.frames_since_match += 1
        if self.lost_count > 10:
            self.match_status.emit("lost")
        elif self.lost_count > 3:
            self.match_status.emit("searching")

    # ================================================================
    #  Lowe ratio test
    # ================================================================

    def _lowe_ratio(self, matches, kp1, kp2):
        """Lowe ratio test 过滤误匹配"""
        good = []
        for m_n in matches:
            if len(m_n) < 2:
                continue
            m, n = m_n
            if m.distance < 0.75 * n.distance:
                good.append(m)
        src = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        return src, dst

    # ================================================================
    #  Kalman 滤波
    # ================================================================

    def _init_kalman(self):
        self.kf = cv2.KalmanFilter(4, 2)
        self.kf.transitionMatrix = np.float32([
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        self.kf.measurementMatrix = np.float32([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 1e-2
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1e-1
        self.kf.statePost = np.zeros((4, 1), dtype=np.float32)

    def _kalman_correct(self, x, y):
        """Kalman 预测 + 修正"""
        self.kf.predict()
        meas = np.float32([[x], [y]])
        corrected = self.kf.correct(meas)
        return float(corrected[0, 0]), float(corrected[1, 0])

    # ================================================================
    #  辅助
    # ================================================================

    def _load_ref_map(self, path):
        """加载参考底图（优先级: coord_mapper -> PIL fallback）"""
        try:
            from coord_mapper import load_map
            bgr = load_map(path)
            if bgr is not None:
                return bgr
        except Exception:
            pass
        from PIL import Image
        img = Image.open(path).convert("RGB")
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    def _estimate_angle(self, src_pts, dst_pts):
        """通过特征点位移估计朝向角"""
        if len(src_pts) < 4:
            return 0.0
        d = dst_pts - src_pts
        return float(np.degrees(np.arctan2(np.mean(d[:, 0, 1]), np.mean(d[:, 0, 0]))))

    def get_last_position(self):
        """返回上次定位坐标或 None"""
        if self.last_px is not None:
            return (self.last_px, self.last_py, self.last_conf)
        return None

    def get_last_frame(self):
        """返回最近一帧 RGB 数组 (h,w,3) 或 None"""
        return self.last_frame

    def shutdown(self):
        """清理信号连接"""
        try:
            self.cap_eng.frame_captured.disconnect(self.on_frame)
        except Exception:
            pass