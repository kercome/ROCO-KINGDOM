"""
tile_mapper.py - 地图切片按需加载工具
数据源: D:\taptap_tiles (231 张 256x256 JPG，X:1016-1031, Y:1016-1031)
"""

import re
import numpy as np
from pathlib import Path
from PIL import Image


class TileMapper:
    """
    按需加载 D:\\taptap_tiles 切片，支持区域查询和整图拼接。
    切片命名: X_Y.jpg，覆盖 4096x4096 底图。
    """

    TILE_SIZE = 256
    MAP_WIDTH = 4096
    MAP_HEIGHT = 4096

    def __init__(self, tiles_dir=r"D:\taptap_tiles"):
        self.tiles_dir = Path(tiles_dir)
        self._tile_index = {}
        self._min_x = self._min_y = float('inf')
        self._max_x = self._max_y = 0
        self._tile_cache = {}
        self._full_map_cache = None
        self._scan_tiles()

    # ---- 内部 ----

    def _scan_tiles(self):
        for f in self.tiles_dir.glob("*.jpg"):
            m = re.match(r"(\d+)_(\d+)\.jpg", f.name)
            if m:
                tx, ty = int(m.group(1)), int(m.group(2))
                self._tile_index[(tx, ty)] = f
                self._min_x = min(self._min_x, tx)
                self._min_y = min(self._min_y, ty)
                self._max_x = max(self._max_x, tx)
                self._max_y = max(self._max_y, ty)

    # ---- 坐标转换 ----

    def pixel_to_tile(self, px, py):
        """像素坐标 -> (tile_x, tile_y, offset_x, offset_y)
        (0, 0) -> (1016, 1016, 0, 0)
        (300, 300) -> (1017, 1017, 44, 44)
        """
        tile_x = self._min_x + int(px // self.TILE_SIZE)
        tile_y = self._min_y + int(py // self.TILE_SIZE)
        ox = int(px % self.TILE_SIZE)
        oy = int(py % self.TILE_SIZE)
        return (tile_x, tile_y, ox, oy)

    def tile_to_pixel(self, tile_x, tile_y):
        """tile坐标 -> 左上角像素坐标
        (1017, 1017) -> (256, 256)
        """
        px = (tile_x - self._min_x) * self.TILE_SIZE
        py = (tile_y - self._min_y) * self.TILE_SIZE
        return (px, py)

    # ---- 切片加载 ----

    def get_tile(self, tile_x, tile_y):
        """返回 256x256x3 np.ndarray (RGB) 或 None"""
        key = (tile_x, tile_y)
        if key in self._tile_cache:
            return self._tile_cache[key]
        if key not in self._tile_index:
            return None
        try:
            img = Image.open(self._tile_index[key])
            arr = np.array(img.convert("RGB"))
            self._tile_cache[key] = arr
            return arr
        except Exception:
            return None

    def load_region(self, pixel_x, pixel_y, width, height):
        """按像素坐标加载地图区域，返回 (height, width, 3) RGB ndarray。
        例: load_region(1500, 2000, 600, 600) -> 600x600 区域
        """
        x1 = max(0, int(pixel_x))
        y1 = max(0, int(pixel_y))
        x2 = min(self.MAP_WIDTH, int(pixel_x + width))
        y2 = min(self.MAP_HEIGHT, int(pixel_y + height))

        if x2 <= x1 or y2 <= y1:
            return np.zeros((0, 0, 3), dtype=np.uint8)

        result = np.zeros((y2 - y1, x2 - x1, 3), dtype=np.uint8)

        tile_x1 = self._min_x + x1 // self.TILE_SIZE
        tile_y1 = self._min_y + y1 // self.TILE_SIZE
        tile_x2 = self._min_x + (x2 - 1) // self.TILE_SIZE
        tile_y2 = self._min_y + (y2 - 1) // self.TILE_SIZE

        for ty in range(tile_y1, tile_y2 + 1):
            for tx in range(tile_x1, tile_x2 + 1):
                tile = self.get_tile(tx, ty)
                if tile is None:
                    continue

                tpx = (tx - self._min_x) * self.TILE_SIZE
                tpy = (ty - self._min_y) * self.TILE_SIZE

                sx1 = max(0, x1 - tpx)
                sy1 = max(0, y1 - tpy)
                sx2 = min(self.TILE_SIZE, x2 - tpx)
                sy2 = min(self.TILE_SIZE, y2 - tpy)

                dx1 = tpx + sx1 - x1
                dy1 = tpy + sy1 - y1
                dx2 = dx1 + (sx2 - sx1)
                dy2 = dy1 + (sy2 - sy1)

                if sx2 > sx1 and sy2 > sy1:
                    result[dy1:dy2, dx1:dx2] = tile[sy1:sy2, sx1:sx2]

        return result

    def get_full_map(self):
        """拼接完整 4096x4096 地图，首次慢后续走缓存。"""
        if self._full_map_cache is not None:
            return self._full_map_cache
        full = np.zeros((self.MAP_HEIGHT, self.MAP_WIDTH, 3), dtype=np.uint8)
        for (tx, ty) in self._tile_index:
            tile = self.get_tile(tx, ty)
            if tile is not None:
                px = (tx - self._min_x) * self.TILE_SIZE
                py = (ty - self._min_y) * self.TILE_SIZE
                full[py:py + self.TILE_SIZE, px:px + self.TILE_SIZE] = tile
        self._full_map_cache = full
        return full

    def clear_cache(self):
        self._tile_cache.clear()
        self._full_map_cache = None

    # ---- 属性 ----

    @property
    def bounds(self):
        return (self._min_x, self._min_y, self._max_x, self._max_y)

    @property
    def pixel_bounds(self):
        return (0, 0, self.MAP_WIDTH, self.MAP_HEIGHT)