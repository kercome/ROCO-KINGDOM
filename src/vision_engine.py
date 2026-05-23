# src/vision_engine.py
import cv2
import numpy as np
import mss
import time
from PyQt5.QtCore import QThread, pyqtSignal

class VisionEngine(QThread):
    # 发射信号: X绝对坐标, Y绝对坐标, 玩家面朝角度, 匹配置信度
    position_updated = pyqtSignal(float, float, float, float)
    
    def __init__(self, big_map_path=r"D:\roco_hd_world_map.v3.jpg"):
        super().__init__()
        self.big_map_path = big_map_path
        self.running = False
        self.delay_ms = 200  # 默认200毫秒捕获一次
        self.roi = {"top": 0, "left": 0, "width": 200, "height": 200}
        
        # 加载世界大底图并提取基准特征
        self.big_map_bgr = cv2.imread(self.big_map_path)
        self.orb = cv2.ORB_create(nfeatures=1500)
        
        # 初始化大图特征字典，用于分块局部搜索(大幅提升性能)
        self.big_kp, self.big_des = self.orb.detectAndCompute(self.big_map_bgr, None)
        
        self.last_x = None
        self.last_y = None

    def set_roi(self, x, y, w, h):
        self.roi = {"top": y, "left": x, "width": w, "height": h}

    def set_delay(self, ms):
        self.delay_ms = ms

    def stop(self):
        self.running = False
        self.wait()

    def get_arrow_angle(self, frame_bgr):
        """核心算法1：提取小地图中心黄色标点指向"""
        h, w = frame_bgr.shape[:2]
        cx, cy = w // 2, h // 2
        
        # 只截取最中心的 40x40 像素区域
        crop = frame_bgr[cy-20:cy+20, cx-20:cx+20]
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        
        # 定义黄色 HSV 阈值 (根据洛克王国游戏内标点微调)
        lower_yellow = np.array([20, 100, 100])
        upper_yellow = np.array([40, 255, 255])
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        # 使用图像矩寻找重心
        M = cv2.moments(mask)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            # 计算从中心(20,20)指向重心的向量角度
            angle_rad = np.arctan2(cY - 20, cX - 20)
            return np.degrees(angle_rad)
        return 0.0

    def run(self):
        self.running = True
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        
        with mss.mss() as sct:
            while self.running:
                start_t = time.time()
                
                # 1. 高速获取屏幕局部画面
                sct_img = sct.grab(self.roi)
                frame = np.frombuffer(sct_img.raw, dtype=np.uint8).reshape((self.roi["height"], self.roi["width"], 4))
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                # 2. 提取面朝角度
                angle = self.get_arrow_angle(frame_bgr)
                
                # 3. 构造圆形掩码去除非地图区域(UI外框)
                h, w = frame_bgr.shape[:2]
                mask = np.zeros((h, w), dtype=np.uint8)
                cv2.circle(mask, (w//2, h//2), min(w,h)//2 - 10, 255, -1)
                
                # 4. 提取当前小地图特征
                kp_small, des_small = self.orb.detectAndCompute(frame_bgr, mask)
                
                # 5. 特征匹配与位置推算
                if des_small is not None and len(des_small) > 10:
                    # 全图匹配 (后期可优化为 last_x, last_y 周围的局部切片匹配以提升性能)
                    matches = bf.match(des_small, self.big_des)
                    matches = sorted(matches, key=lambda x: x.distance)
                    
                    good_matches = matches[:20] # 取前20个最佳匹配
                    if len(good_matches) > 8:
                        src_pts = np.float32([kp_small[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        dst_pts = np.float32([self.big_kp[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        
                        # 计算单应性矩阵映射
                        M, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                        if M is not None:
                            # 映射小地图中心点到大地图
                            center_pt = np.float32([[[w/2, h/2]]])
                            mapped_pt = cv2.perspectiveTransform(center_pt, M)
                            
                            self.last_x = float(mapped_pt[0][0][0])
                            self.last_y = float(mapped_pt[0][0][1])
                            
                            # 发射坐标、角度与置信度
                            self.position_updated.emit(self.last_x, self.last_y, angle, 1.0)
                
                # 严格控制截取频率 (毫秒延迟)
                elapsed = time.time() - start_t
                sleep_time = max(0, (self.delay_ms / 1000.0) - elapsed)
                time.sleep(sleep_time)