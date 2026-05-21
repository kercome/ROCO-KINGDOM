#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
坐标对齐引擎 (Coord_Align)
功能：将视觉引擎定位结果与外部点位数据集做空间对齐和最近邻搜索
"""

import json
import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any


PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_JSON_PATH = str(PROJECT_ROOT / "data" / "aligned_points.json")


def load_points(json_path: str) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
    """
    加载 aligned_points.json，返回 areas、regions、types、type_groups
    
    Args:
        json_path: aligned_points.json 的路径
        
    Returns:
        (areas, regions, types, type_groups)
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    areas = data.get('areas', [])
    regions = data.get('regions', [])
    types = data.get('types', [])
    type_groups = data.get('type_groups', [])
    
    return areas, regions, types, type_groups


def pixel_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    计算两个像素坐标之间的欧氏距离
    
    Args:
        x1, y1: 第一个点的坐标
        x2, y2: 第二个点的坐标
        
    Returns:
        欧氏距离（像素）
    """
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


class CoordAligner:
    """
    坐标对齐引擎，提供空间索引和最近邻搜索功能
    """
    
    def __init__(self, json_path: Optional[str] = None):
        """
        初始化坐标对齐引擎
        
        Args:
            json_path: aligned_points.json 的路径，如果为 None 则使用默认路径
        """
        if json_path is None:
            json_path = DEFAULT_JSON_PATH
        
        # 加载数据
        self.areas, self.regions, self.types, self.type_groups = load_points(json_path)
        
        # 构建所有点位的列表 (areas + regions)
        self.all_points = []
        self.all_points.extend(self.areas)
        self.all_points.extend(self.regions)
        
        # 构建 KD-Tree 的空间点列表
        self._build_kdtree()
        
        # 构建快速查找索引
        self._build_indices()
        
        print(f"[CoordAligner] 初始化完成")
        print(f"  - 加载 {len(self.areas)} 个 areas")
        print(f"  - 加载 {len(self.regions)} 个 regions")
        print(f"  - 加载 {len(self.types)} 个 types")
        print(f"  - 加载 {len(self.type_groups)} 个 type_groups")
        print(f"  - KD-Tree 包含 {len(self.all_points)} 个点位")
    
    def _build_kdtree(self):
        """构建 KD-Tree 空间索引"""
        try:
            from scipy.spatial import KDTree
            
            # 提取所有点位的像素坐标
            coords = []
            for point in self.all_points:
                px = point.get('pixel_x', 0)
                py = point.get('pixel_y', 0)
                coords.append([px, py])
            
            # 构建 KD-Tree
            self.kdtree = KDTree(coords)
            self.kdtree_available = True
            print(f"[CoordAligner] KD-Tree 构建成功")
            
        except ImportError:
            self.kdtree = None
            self.kdtree_available = False
            print(f"[CoordAligner] 警告: scipy 未安装，KD-Tree 不可用，将使用暴力搜索")
    
    def _build_indices(self):
        """构建快速查找索引"""
        # region_id -> region
        self.region_dict = {r['id']: r for r in self.regions}
        
        # area_id -> area
        self.area_dict = {a['id']: a for a in self.areas}
        
        # type_id -> type
        self.type_dict = {t['id']: t for t in self.types}
        
        # type_group_id -> type_group
        self.type_group_dict = {g['id']: g for g in self.type_groups}
        
        # region_id -> types (该区域下的所有类型)
        self.region_types = {}
        for t in self.types:
            region_ids_str = t.get('region_ids', '')
            if region_ids_str:
                region_ids = [int(rid.strip()) for rid in region_ids_str.split(',') if rid.strip()]
                for rid in region_ids:
                    if rid not in self.region_types:
                        self.region_types[rid] = []
                    self.region_types[rid].append(t)
        
        # type_group_id -> types
        self.group_types = {}
        for t in self.types:
            group_ids_str = t.get('group_ids', '')
            if group_ids_str:
                group_ids = [int(gid.strip()) for gid in group_ids_str.split(',') if gid.strip()]
                for gid in group_ids:
                    if gid not in self.group_types:
                        self.group_types[gid] = []
                    self.group_types[gid].append(t)
    
    def find_nearest(self, px: float, py: float, max_distance: Optional[float] = None, count: int = 5) -> List[Tuple[Dict, float]]:
        """
        查找 (px, py) 附近最近的 N 个点位
        
        Args:
            px, py: 查询点的像素坐标
            max_distance: 最大搜索距离（像素），None 表示无限制
            count: 最多返回的点位数量
            
        Returns:
            [(point_dict, distance_px), ...] 按距离升序排列
        """
        if self.kdtree_available and self.kdtree is not None:
            return self._find_nearest_kdtree(px, py, max_distance, count)
        else:
            return self._find_nearest_bruteforce(px, py, max_distance, count)
    
    def _find_nearest_kdtree(self, px: float, py: float, max_distance: Optional[float], count: int) -> List[Tuple[Dict, float]]:
        """使用 KD-Tree 查找最近邻"""
        import numpy as np
        
        # 查询最近的点
        k = min(count, len(self.all_points))
        distances, indices = self.kdtree.query([px, py], k=k)
        
        # 确保是数组（当 k=1 时可能返回标量）
        if np.isscalar(distances):
            distances = [distances]
            indices = [indices]
        else:
            distances = list(distances)
            indices = list(indices)
        
        # 构建结果列表
        results = []
        for dist, idx in zip(distances, indices):
            idx_int = int(idx)
            if 0 <= idx_int < len(self.all_points):
                point = self.all_points[idx_int]
                
                # 检查距离限制
                if max_distance is not None and dist > max_distance:
                    continue
                
                results.append((point, float(dist)))
        
        return results
    
    def _find_nearest_bruteforce(self, px: float, py: float, max_distance: Optional[float], count: int) -> List[Tuple[Dict, float]]:
        """使用暴力搜索查找最近邻"""
        distances = []
        
        for point in self.all_points:
            point_px = point.get('pixel_x', 0)
            point_py = point.get('pixel_y', 0)
            
            dist = pixel_distance(px, py, point_px, point_py)
            
            # 检查距离限制
            if max_distance is not None and dist > max_distance:
                continue
            
            distances.append((point, dist))
        
        # 按距离排序
        distances.sort(key=lambda x: x[1])
        
        # 返回前 count 个结果
        return distances[:count]
    
    def find_by_region(self, region_id: int) -> Dict[str, Any]:
        """
        根据 region_id 查找该区域的所有点位和类型
        
        Args:
            region_id: 区域 ID
            
        Returns:
            {
                'region': region_dict,
                'types': [type_dict, ...],
                'area': area_dict (如果有)
            }
        """
        result = {
            'region': None,
            'types': [],
            'area': None
        }
        
        # 查找 region
        if region_id in self.region_dict:
            result['region'] = self.region_dict[region_id]
        
        # 查找该区域的 types
        if region_id in self.region_types:
            result['types'] = self.region_types[region_id]
        
        # 尝试查找该 region 所属的 area (根据像素坐标的距离)
        if result['region']:
            region_px = result['region'].get('pixel_x', 0)
            region_py = result['region'].get('pixel_y', 0)
            
            min_dist = float('inf')
            closest_area = None
            
            for area in self.areas:
                area_px = area.get('pixel_x', 0)
                area_py = area.get('pixel_y', 0)
                dist = pixel_distance(region_px, region_py, area_px, area_py)
                
                if dist < min_dist:
                    min_dist = dist
                    closest_area = area
            
            result['area'] = closest_area
            result['distance_to_area'] = min_dist
        
        return result
    
    def get_area_info(self, px: float, py: float) -> Dict[str, Any]:
        """
        判断 (px, py) 属于哪个 area
        
        Args:
            px, py: 像素坐标
            
        Returns:
            {
                'area': area_dict (最近的 area),
                'distance': 距离（像素）
            }
        """
        if not self.areas:
            return {'area': None, 'distance': float('inf')}
        
        min_dist = float('inf')
        closest_area = None
        
        for area in self.areas:
            area_px = area.get('pixel_x', 0)
            area_py = area.get('pixel_y', 0)
            dist = pixel_distance(px, py, area_px, area_py)
            
            if dist < min_dist:
                min_dist = dist
                closest_area = area
        
        return {
            'area': closest_area,
            'distance': min_dist
        }
    
    def get_nearby_types(self, px: float, py: float, radius: float = 500) -> List[Dict]:
        """
        返回指定半径内的所有点位类型
        
        Args:
            px, py: 中心点的像素坐标
            radius: 搜索半径（像素），默认 500
            
        Returns:
            [{'type': type_dict, 'region': region_dict, 'distance': float}, ...]
        """
        results = []
        seen_types = set()
        
        # 遍历所有 regions，找到半径内的 region
        for region in self.regions:
            region_px = region.get('pixel_x', 0)
            region_py = region.get('pixel_y', 0)
            
            dist = pixel_distance(px, py, region_px, region_py)
            
            if dist <= radius:
                # 找到该 region 下的所有 types
                region_id = region['id']
                if region_id in self.region_types:
                    for t in self.region_types[region_id]:
                        type_id = t['id']
                        if type_id not in seen_types:
                            seen_types.add(type_id)
                            results.append({
                                'type': t,
                                'region': region,
                                'distance': dist
                            })
        
        # 按距离排序
        results.sort(key=lambda x: x['distance'])
        
        return results
    
    def get_route_info(self, region_ids: List[int]) -> Dict[str, Any]:
        """
        根据 region_ids 获取关联的类型和图标信息
        
        Args:
            region_ids: 区域 ID 列表
            
        Returns:
            {
                'regions': [region_dict, ...],
                'types': [type_dict, ...],
                'type_groups': [type_group_dict, ...],
                'icons': [icon_url, ...]
            }
        """
        result = {
            'regions': [],
            'types': [],
            'type_groups': [],
            'icons': []
        }
        
        seen_types = set()
        seen_groups = set()
        
        for rid in region_ids:
            # 添加 region
            if rid in self.region_dict:
                result['regions'].append(self.region_dict[rid])
                
                # 添加该 region 下的 types
                if rid in self.region_types:
                    for t in self.region_types[rid]:
                        if t['id'] not in seen_types:
                            seen_types.add(t['id'])
                            result['types'].append(t)
                            
                            # 收集图标
                            if 'icon' in t and t['icon']:
                                result['icons'].append(t['icon'])
                            
                            # 收集 type_groups
                            group_ids_str = t.get('group_ids', '')
                            if group_ids_str:
                                group_ids = [int(gid.strip()) for gid in group_ids_str.split(',') if gid.strip()]
                                for gid in group_ids:
                                    if gid not in seen_groups and gid in self.type_group_dict:
                                        seen_groups.add(gid)
                                        result['type_groups'].append(self.type_group_dict[gid])
        
        return result
    
    def get_current_position(self) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        模拟 vision_engine.get_current_position() 的接口
        
        Returns:
            (x, y, theta, confidence) 或 (None, None, None, None) 如果无法定位
        """
        # 这里应该调用实际的视觉引擎
        # 目前返回 None 表示需要实际实现
        print("[CoordAligner] 警告: vision_engine 未连接，返回模拟数据")
        
        # 返回模拟数据（地图中心附近）
        map_center_x = 2048
        map_center_y = 2048
        theta = 0.0
        confidence = 0.0
        
        return (map_center_x, map_center_y, theta, confidence)


def main():
    """测试主函数"""
    print("=" * 60)
    print("坐标对齐引擎测试")
    print("=" * 60)
    
    # 初始化
    aligner = CoordAligner()
    
    print("\n" + "=" * 60)
    print("测试 1: find_nearest")
    print("=" * 60)
    
    # 测试 find_nearest
    test_x, test_y = 2048, 2048  # 地图中心
    nearest = aligner.find_nearest(test_x, test_y, count=5)
    
    print(f"\n查询点: ({test_x}, {test_y})")
    print(f"找到 {len(nearest)} 个最近点位:\n")
    
    for i, (point, dist) in enumerate(nearest, 1):
        title = point.get('title', 'N/A')
        px = point.get('pixel_x', 0)
        py = point.get('pixel_y', 0)
        print(f"  {i}. {title} - 距离: {dist:.2f}px ({px}, {py})")
    
    print("\n" + "=" * 60)
    print("测试 2: get_area_info")
    print("=" * 60)
    
    # 测试 get_area_info
    area_info = aligner.get_area_info(test_x, test_y)
    if area_info['area']:
        print(f"\n点 ({test_x}, {test_y}) 最近的 area:")
        print(f"  - {area_info['area']['title']}")
        print(f"  - 距离: {area_info['distance']:.2f}px")
    
    print("\n" + "=" * 60)
    print("测试 3: find_by_region")
    print("=" * 60)
    
    # 测试 find_by_region
    if aligner.regions:
        test_region_id = aligner.regions[0]['id']
        region_info = aligner.find_by_region(test_region_id)
        
        print(f"\nRegion ID {test_region_id}:")
        if region_info['region']:
            print(f"  - Region: {region_info['region'].get('title', 'N/A')}")
            print(f"  - Types: {len(region_info['types'])} 个")
            if region_info['area']:
                print(f"  - 所属 Area: {region_info['area']['title']}")
    
    print("\n" + "=" * 60)
    print("测试 4: get_nearby_types")
    print("=" * 60)
    
    # 测试 get_nearby_types
    nearby_types = aligner.get_nearby_types(test_x, test_y, radius=1000)
    print(f"\n半径 1000px 内的类型: {len(nearby_types)} 个")
    for i, item in enumerate(nearby_types[:5], 1):
        t = item['type']
        print(f"  {i}. {t.get('title', 'N/A')} - 距离: {item['distance']:.2f}px")
    
    print("\n" + "=" * 60)
    print("测试 5: get_route_info")
    print("=" * 60)
    
    # 测试 get_route_info
    if len(aligner.regions) >= 3:
        test_region_ids = [r['id'] for r in aligner.regions[:3]]
        route_info = aligner.get_route_info(test_region_ids)
        
        print(f"\nRoute 包含 {len(test_region_ids)} 个 regions:")
        print(f"  - Regions: {len(route_info['regions'])} 个")
        print(f"  - Types: {len(route_info['types'])} 个")
        print(f"  - Type Groups: {len(route_info['type_groups'])} 个")
        print(f"  - Icons: {len(route_info['icons'])} 个")
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
