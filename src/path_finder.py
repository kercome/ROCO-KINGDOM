"""
path_finder.py
A* 路径规划引擎 - Roco Navigation Tool

功能：
  在 4096x4096 底图上做 A* 路径规划，从玩家位置导航到目标点位。

航点网络：
  - 从 aligned_points.json 加载 areas + regions 作为导航节点
  - 基于像素距离构建邻接图
  - 使用 A* 算法搜索最优路径

依赖：
  - coord_mapper: 坐标映射常量
  - vision_engine: 获取玩家当前位置 (get_current_position)
"""

import json
import math
import heapq
import os
from typing import Optional, List, Dict, Tuple, Any

# ── 常量 ────────────────────────────────────────────────────
MAP_WIDTH = 4096
MAP_HEIGHT = 4096
DEFAULT_CONNECTION_RADIUS = 1500      # 航点连接半径（像素）
MAX_ITERATIONS = 20000                # A* 最大迭代次数


# ═══════════════════════════════════════════════════════════
#  PathFinder
# ═══════════════════════════════════════════════════════════

class PathFinder:
    """
    A* 路径规划引擎

    通过航点网络（waypoint graph）在底图上搜索最优路径。
    航点来源于 aligned_points.json 中的 areas 和 regions。
    """

    def __init__(self, aligned_points_path: Optional[str] = None,
                 coord_mapper=None):
        """
        初始化路径规划器

        Args:
            aligned_points_path: aligned_points.json 路径
            coord_mapper: coord_mapper 模块引用（可选）
        """
        if aligned_points_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            aligned_points_path = os.path.join(base_dir, "aligned_points.json")

        self.coord_mapper = coord_mapper
        self.areas: List[Dict] = []
        self.regions: List[Dict] = []
        self.all_waypoints: List[Dict] = []
        self.waypoint_index: Dict[str, Dict] = {}   # key: "area_{id}" or "region_{id}"
        self.graph: Dict[str, List[Tuple[str, float]]] = {}  # adjacency list
        self._node_list: List[str] = []              # ordered node keys

        # 加载数据
        self._load_points(aligned_points_path)

    # ── 数据加载 ──────────────────────────────────────────

    def _load_points(self, path: str) -> None:
        """从 JSON 加载航点数据并构建图"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.areas = data.get("areas", [])
        self.regions = data.get("regions", [])

        # 合并建立航点索引
        self.all_waypoints = []
        for area in self.areas:
            key = f"area_{area['id']}"
            wp = dict(area)
            wp["_key"] = key
            wp["_type"] = "area"
            self.all_waypoints.append(wp)
            self.waypoint_index[key] = wp
            self._node_list.append(key)

        for region in self.regions:
            key = f"region_{region['id']}"
            wp = dict(region)
            wp["_key"] = key
            wp["_type"] = "region"
            self.all_waypoints.append(wp)
            self.waypoint_index[key] = wp
            self._node_list.append(key)

        # 构建图
        self.build_waypoint_graph()

    # ── 图构建 ────────────────────────────────────────────

    def build_waypoint_graph(self, connection_radius: float = DEFAULT_CONNECTION_RADIUS) -> None:
        """
        基于像素距离构建航点网络图。
        两个航点若距离 < connection_radius 像素，则建立双向边。

        Args:
            connection_radius: 连接半径（像素），默认 1500
        """
        self.connection_radius = connection_radius
        n = len(self.all_waypoints)

        # 初始化邻接表
        self.graph = {node: [] for node in self._node_list}

        # 提取坐标数组（加速）
        coords = [(wp["pixel_x"], wp["pixel_y"]) for wp in self.all_waypoints]

        for i in range(n):
            xi, yi = coords[i]
            key_i = self._node_list[i]

            for j in range(i + 1, n):
                xj, yj = coords[j]
                key_j = self._node_list[j]

                dist = math.hypot(xj - xi, yj - yi)
                if dist < connection_radius:
                    self.graph[key_i].append((key_j, dist))
                    self.graph[key_j].append((key_i, dist))

    # ── 启发函数 ──────────────────────────────────────────

    @staticmethod
    def heuristic(x1: float, y1: float, x2: float, y2: float) -> float:
        """启发函数：欧氏距离"""
        return math.hypot(x2 - x1, y2 - y1)

    # ── A* 核心算法 ──────────────────────────────────────

    def a_star(self, start_px: float, start_py: float,
               goal_px: float, goal_py: float) -> Dict[str, Any]:
        """
        A* 路径搜索。

        Args:
            start_px, start_py: 起点的像素坐标
            goal_px, goal_py:  终点的像素坐标

        Returns:
            {
                'path': [(x1,y1), (x2,y2), ...],   # 像素坐标路径（含起点和终点）
                'distance': float,                   # 总路径长度（像素）
                'waypoints': [dict, ...],            # 经过的航点
                'iterations': int                    # 搜索迭代次数
            }
            若无法到达则返回 {'path': [], 'distance': float('inf'), ...}
        """
        # Step 1: 找到离起点/终点最近的航点
        start_node = self._nearest_waypoint(start_px, start_py)
        goal_node = self._nearest_waypoint(goal_px, goal_py)

        start_key = start_node["_key"]
        goal_key = goal_node["_key"]

        # 同一节点直接返回
        if start_key == goal_key:
            return self._direct_path(start_px, start_py, goal_px, goal_py,
                                     [start_node])

        # Step 2: A* 搜索
        # open_set: (f_score, tiebreaker, node_key)
        tiebreaker = 0
        open_set: List[Tuple[float, int, str]] = []
        heapq.heappush(open_set, (0.0, 0, start_key))

        came_from: Dict[str, Optional[str]] = {start_key: None}
        g_score: Dict[str, float] = {start_key: 0.0}
        closed_set: set = set()
        iterations = 0

        while open_set and iterations < MAX_ITERATIONS:
            iterations += 1
            f_score, _, current = heapq.heappop(open_set)

            if current in closed_set:
                continue

            if current == goal_key:
                break

            closed_set.add(current)

            for neighbor_key, edge_weight in self.graph.get(current, []):
                if neighbor_key in closed_set:
                    continue

                tentative_g = g_score[current] + edge_weight

                if tentative_g < g_score.get(neighbor_key, float("inf")):
                    came_from[neighbor_key] = current
                    g_score[neighbor_key] = tentative_g

                    wp = self.waypoint_index[neighbor_key]
                    h = self.heuristic(wp["pixel_x"], wp["pixel_y"],
                                       goal_node["pixel_x"], goal_node["pixel_y"])
                    f = tentative_g + h
                    tiebreaker += 1
                    heapq.heappush(open_set, (f, tiebreaker, neighbor_key))

        # Step 3: 路径回溯
        if goal_key not in came_from or iterations >= MAX_ITERATIONS:
            return {
                "path": [],
                "distance": float("inf"),
                "waypoints": [],
                "iterations": iterations
            }

        # 回溯节点序列
        node_sequence = []
        cur = goal_key
        while cur is not None:
            node_sequence.append(cur)
            cur = came_from.get(cur)
        node_sequence.reverse()

        # Step 4: 构建完整像素路径
        path = [(start_px, start_py)]
        waypoints = []

        for node_key in node_sequence:
            wp = self.waypoint_index[node_key]
            path.append((wp["pixel_x"], wp["pixel_y"]))
            waypoints.append(wp)

        path.append((goal_px, goal_py))

        # 计算总距离
        total_dist = self._path_distance(path)

        return {
            "path": path,
            "distance": total_dist,
            "waypoints": waypoints,
            "iterations": iterations
        }

    # ── 查找最近点位路线 ──────────────────────────────────

    def find_route_to_nearest(self, player_px: float, player_py: float,
                               point_type: Optional[str] = None,
                               region_name: Optional[str] = None) -> Dict[str, Any]:
        """
        查找玩家到最近指定类型点位的路线。

        Args:
            player_px, player_py: 玩家像素坐标
            point_type: 点位类型 ("area" / "region" / None=全部)
            region_name: 区域名称筛选（可选，模糊匹配 title）

        Returns:
            与 a_star 相同的字典结构，外加 'target' 字段
        """
        # 筛选候选目标
        candidates = []
        if point_type == "area":
            candidates = self.areas
        elif point_type == "region":
            candidates = self.regions
        else:
            candidates = self.all_waypoints

        if region_name:
            candidates = [c for c in candidates
                          if region_name.lower() in (c.get("title", "") or "").lower()]

        if not candidates:
            return {
                "path": [],
                "distance": float("inf"),
                "waypoints": [],
                "iterations": 0,
                "target": None
            }

        # 找最近的
        nearest = min(candidates,
                      key=lambda c: self.heuristic(player_px, player_py,
                                                   c["pixel_x"], c["pixel_y"]))

        result = self.a_star(player_px, player_py,
                             nearest["pixel_x"], nearest["pixel_y"])
        result["target"] = nearest
        return result

    # ── 辅助方法 ──────────────────────────────────────────

    def _nearest_waypoint(self, px: float, py: float) -> Dict:
        """找到最近的航点"""
        best = None
        best_dist = float("inf")
        for wp in self.all_waypoints:
            d = self.heuristic(px, py, wp["pixel_x"], wp["pixel_y"])
            if d < best_dist:
                best_dist = d
                best = wp
        return best

    @staticmethod
    def _direct_path(sx: float, sy: float, gx: float, gy: float,
                     waypoints: List[Dict]) -> Dict[str, Any]:
        """起终点在同一航点时的直连路径"""
        path = [(sx, sy), (gx, gy)]
        return {
            "path": path,
            "distance": math.hypot(gx - sx, gy - sy),
            "waypoints": waypoints,
            "iterations": 1
        }

    @staticmethod
    def _path_distance(path: List[Tuple[float, float]]) -> float:
        """计算路径总长度"""
        total = 0.0
        for i in range(1, len(path)):
            x1, y1 = path[i - 1]
            x2, y2 = path[i]
            total += math.hypot(x2 - x1, y2 - y1)
        return total

    @staticmethod
    def distance(path: List[Tuple[float, float]]) -> float:
        """计算路径总长度（公开接口）"""
        return PathFinder._path_distance(path)

    def format_path(self, path_result: Dict[str, Any]) -> str:
        """将路径结果格式化为可读字符串"""
        if not path_result.get("path"):
            return "[无路径] 目标不可达"

        lines = [
            f"路径规划结果:",
            f"  距离: {path_result['distance']:.2f} 像素",
            f"  航点数: {len(path_result.get('waypoints', []))}",
            f"  迭代次数: {path_result.get('iterations', 0)}",
        ]

        if path_result.get("target"):
            t = path_result["target"]
            lines.append(f"  目标: [{t.get('_type', '')}] {t.get('title', '')} (id={t.get('id', '')})")

        lines.append("  路径节点:")
        for i, (px, py) in enumerate(path_result["path"]):
            marker = ""
            for wp in path_result.get("waypoints", []):
                if abs(wp["pixel_x"] - px) < 1 and abs(wp["pixel_y"] - py) < 1:
                    marker = f" --> [{wp.get('_type', '')}] {wp.get('title', wp.get('id', ''))}"
                    break
            lines.append(f"    {i}: ({px:.1f}, {py:.1f}){marker}")

        return "\n".join(lines)

    def path_to_waypoints(self, path: List[Tuple[float, float]]) -> List[Dict]:
        """将像素路径映射回数据点位"""
        result = []
        for px, py in path:
            best = None
            best_dist = float("inf")
            for wp in self.all_waypoints:
                d = self.heuristic(px, py, wp["pixel_x"], wp["pixel_y"])
                if d < best_dist:
                    best_dist = d
                    best = wp

            # 只有在很近（< 50px）时才算匹配
            if best_dist < 50:
                result.append(best)
            else:
                result.append({"pixel_x": px, "pixel_y": py, "_type": "waypoint"})
        return result

    # ── 从 VisionEngine 获取位置 ──────────────────────────

    def navigate_from_player(self, target_px: float, target_py: float,
                              vision_engine: Optional[Any] = None) -> Dict[str, Any]:
        """
        从玩家当前位置导航到目标点位。

        Args:
            target_px, target_py: 目标像素坐标
            vision_engine: VisionEngine 实例（可选）

        Returns:
            A* 结果字典，含 'player_position' 字段
        """
        if vision_engine is not None:
            pos = vision_engine.get_current_position()
            if pos is None:
                raise RuntimeError("VisionEngine 无法获取玩家位置")

            player_px, player_py, theta, confidence = pos
        else:
            # 无 vision_engine 时的模拟
            player_px, player_py = MAP_WIDTH // 2, MAP_HEIGHT // 2

        result = self.a_star(player_px, player_py, target_px, target_py)
        result["player_position"] = (player_px, player_py)
        return result


# ── 自检 ────────────────────────────────────────────────────
if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    points_path = os.path.join(base_dir, "aligned_points.json")

    pf = PathFinder(aligned_points_path=points_path)
    print(f"PathFinder 初始化完成")
    print(f"  areas:   {len(pf.areas)} 个")
    print(f"  regions: {len(pf.regions)} 个")
    print(f"  航点总数: {len(pf.all_waypoints)} 个")
    print(f"  图节点数: {len(pf.graph)} 个")
    edge_count = sum(len(v) for v in pf.graph.values()) // 2
    print(f"  图边数:   {edge_count} 条")
    print(f"  连接半径: {DEFAULT_CONNECTION_RADIUS} px")

    # 测试 A*
    result = pf.a_star(1000, 1000, 3000, 3000)
    print(f"\n--- A* 测试: (1000,1000) -> (3000,3000) ---")
    print(pf.format_path(result))