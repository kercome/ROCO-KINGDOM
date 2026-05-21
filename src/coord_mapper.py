"""
coord_mapper.py
坐标映射模块 - Roco Navigation Tool

地图基准信息（由基准地图预处理步骤1自动生成）：
  - 原图路径: roco_hd_world_map.v3.png
  - 图像尺寸: MAP_WIDTH x MAP_HEIGHT = 4096 x 4096
  - 图像模式: RGBA
  - 原点:     图像左上角 (0, 0)
  - 金字塔目录: pyramid/
"""

from PIL import Image
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# ── 图像尺寸常量 ─────────────────────────────────────────────
MAP_WIDTH  = 4096   # 原图宽度（像素）
MAP_HEIGHT = 4096   # 原图高度（像素）
MAP_MODE   = "RGBA"

# ── 坐标转换函数 ────────────────────────────────────────────

def pixel_to_game_coords(x: int, y: int, zoom: float = 1.0) -> tuple:
    """
    将像素坐标 (x, y) 转换为游戏网格坐标。
    原点: 大图左上角 (0, 0)。zoom 为当前金字塔等级。
    返回: (game_x, game_y)
    """
    return (int(x / zoom), int(y / zoom))


def game_to_pixel(x: int, y: int, zoom: float = 1.0) -> tuple:
    """
    将游戏网格坐标转换回像素坐标。
    返回: (pixel_x, pixel_y)
    """
    return (int(x * zoom), int(y * zoom))


# ── 金字塔加载函数 ──────────────────────────────────────────

def load_map(zoom: float = 1.0) -> Image.Image:
    """
    根据缩放等级加载对应的金字塔图像。
    支持的 zoom 值: 1.0 / 0.75 / 0.5
    返回: PIL.Image.Image 对象
    """
    base_dir = PROJECT_ROOT / "assets" / "maps"
    pyramid_dir = base_dir / "pyramid"

    zoom_file_map = {
        1.0:  "zoom_1.0.png",
        0.75: "zoom_0.75.png",
        0.5:  "zoom_0.5.png",
    }

    # 选取最接近的可用等级
    available_zooms = sorted(zoom_file_map.keys(), key=lambda z: abs(z - zoom))
    best_zoom = available_zooms[0]
    filename = zoom_file_map[best_zoom]
    path = os.path.join(pyramid_dir, filename)

    if not os.path.exists(path):
        raise FileNotFoundError(f"金字塔切片未找到: {path}")

    img = Image.open(path)
    return img


def get_map_size(zoom: float = 1.0) -> tuple:
    """
    返回指定 zoom 等级下的地图尺寸 (width, height)。
    """
    img = load_map(zoom)
    return img.size


# ── 自检 ────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"MAP_WIDTH  = {MAP_WIDTH}")
    print(f"MAP_HEIGHT = {MAP_HEIGHT}")
    print(f"MAP_MODE   = {MAP_MODE}")

    # 坐标映射自检
    px, py = 2048, 2048
    gx, gy = pixel_to_game_coords(px, py, zoom=1.0)
    print(f"pixel_to_game({px}, {py}, zoom=1.0) = {(gx, gy)}")

    bx, by = game_to_pixel(gx, gy, zoom=1.0)
    print(f"game_to_pixel({gx}, {gy}, zoom=1.0) = {(bx, by)}")

    # 加载金字塔自检
    for z in (1.0, 0.75, 0.5):
        img = load_map(z)
        print(f"load_map(zoom={z}) -> {img.size[0]}x{img.size[1]} {img.mode}")
