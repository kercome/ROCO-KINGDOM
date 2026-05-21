# 洛克王国 · 视觉导航叠加工具

> Roco Kingdom — Visual Navigation Overlay Tool

基于 **视觉定位 + 坐标映射 + A\* 路径规划** 的《洛克王国》端游实时导航辅助工具。  
通过窗口捕获 → ORB 特征匹配 → 坐标解算 → 路径搜索 → PyQt5 半透明雷达叠加，实现游戏内实时导航指引。

---

## ✨ 功能特性

| 模块 | 功能 | 技术栈 |
|------|------|---------|
| 🗺️ 坐标映射 | 像素↔️游戏坐标双向转换 | numpy / Pillow |
| 📍 点位对齐 | 341+ 采集点 KD-Tree 空间索引 | scipy.spatial.KDTree |
| 🧭 路径规划 | A\* 算法，40 节点 / 265 边航点图 | heapq / numpy |
| 👁️ 视觉定位 | ORB 特征匹配 + Kalman 滤波 + 单应性矩阵 | OpenCV / numpy |
| 🖥️ 窗口捕获 | Windows 游戏窗口实时截图 | mss / win32gui |
| 🎯 雷达叠加 | 半透明 PyQt5 叠加层，跟随游戏窗口 | PyQt5 / QGraphicsView |
| 🎛️ 控制面板 | 目标选择 / 路线管理 / 显示开关 | PyQt5 / QComboBox |

---

## 📦 目录结构

```
Roco/
├── main.py                 # 主入口
├── src/                    # 核心模块
│   ├── coord_mapper.py     # 坐标映射
│   ├── coord_aligner.py    # 点位对齐（KDTree）
│   ├── path_finder.py      # A* 路径规划
│   ├── vision_engine.py    # ORB + Kalman 视觉定位
│   ├── overlay_ui.py       # 雷达叠加层 UI
│   └── control_panel.py    # 控制面板
├── data/                   # 数据文件
│   ├── aligned_points.json # 341 个采集点（像素 + 经纬度）
│   └── web_data.txt        # TapTap 地图原始数据
├── assets/                 # 资源文件
│   └── maps/              # 游戏地图金字塔
│       ├── roco_hd_world_map.v3.png
│       └── pyramid/        # 多分辨率金字塔
├── tests/                  # 测试用例
├── scripts/                # 调试 / 辅助脚本
├── requirements.txt         # Python 依赖
├── .gitignore
└── README.md
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动工具

```bash
python main.py
```

### 3. 使用流程

1. 打开《洛克王国》客户端，登录游戏
2. 启动工具，点击「🔗 连接游戏」
3. 在控制面板选择目标点位
4. 雷达叠加层将自动显示当前位置 + 导航路线

---

## 🔧 核心模块说明

### `coord_mapper.py`
将地图像素坐标 (px, py) 映射为游戏内经纬度 (lng, lat)，支持双向转换。  
地图基准尺寸：`4096 × 4096`。

### `coord_aligner.py`
基于 `scipy.spatial.KDTree` 构建空间索引，支持：
- 最近点位查询
- 区域筛选
- 范围搜索

### `path_finder.py`
A\* 路径搜索， Euclidean 距离启发函数。  
航点图规模：40 节点 / 265 边（connection_radius = 1500px）。

### `vision_engine.py`
视觉定位引擎：
1. `mss` 截取游戏窗口画面
2. ORB 特征点匹配（参考地图）
3. 单应性矩阵解算相机位姿
4. Kalman 滤波平滑位置估计

### `overlay_ui.py`
PyQt5 半透明叠加窗口（`Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint`）：
- 左上角：小地图（200×200，实时位置标记）
- 右上角：点位信息面板
- 底部：状态栏（坐标 / 朝向 / FPS）

### `control_panel.py`
控制台面板：
- 连接 / 断开游戏
- 目标点位下拉选择
- 显示开关（雷达 / 路线 / 信息面板）

---

## 📋 依赖环境

- Python ≥ 3.10
- PyQt5 ≥ 5.15
- OpenCV ≥ 4.8（`opencv-python-headless`）
- numpy / scipy / Pillow
- mss / pywin32（Windows 窗口捕获）

详见 [`requirements.txt`](./requirements.txt)。

---

## ⚠️ 免责声明

本工具为**技术研究项目**，仅用于学习游戏导航算法（坐标映射、路径规划、视觉定位）。  
**请勿用于破坏游戏平衡的自动化操作。** 使用本工具产生的任何后果由使用者自行承担。

---

## 📄 License

MIT License — 详见 [LICENSE](./LICENSE)
