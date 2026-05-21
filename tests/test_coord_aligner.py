#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
坐标对齐引擎 - 端到端测试脚本
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coord_aligner import CoordAligner, load_points, pixel_distance


def test_load_points():
    """测试数据加载"""
    print("\n" + "=" * 60)
    print("测试 1: 数据加载")
    print("=" * 60)
    
    json_path = r"D:\Roco_Navigation_Tool_Workspace\aligned_points.json"
    areas, regions, types, type_groups = load_points(json_path)
    
    print(f"✅ areas: {len(areas)} 个")
    print(f"✅ regions: {len(regions)} 个")
    print(f"✅ types: {len(types)} 个")
    print(f"✅ type_groups: {len(type_groups)} 个")
    
    assert len(areas) == 4, f"预期 4 个 areas, 实际 {len(areas)}"
    assert len(regions) == 36, f"预期 36 个 regions, 实际 {len(regions)}"
    assert len(types) > 0, "types 应为非空"
    assert len(type_groups) > 0, "type_groups 应为非空"
    
    print("\n✅ 数据加载测试通过")
    return True


def test_coord_aligner_init():
    """测试 CoordAligner 初始化"""
    print("\n" + "=" * 60)
    print("测试 2: CoordAligner 初始化")
    print("=" * 60)
    
    aligner = CoordAligner()
    
    print(f"✅ KD-Tree 可用: {aligner.kdtree_available}")
    print(f"✅ 总点位数: {len(aligner.all_points)}")
    print(f"✅ Areas 索引: {len(aligner.area_dict)} 个")
    print(f"✅ Regions 索引: {len(aligner.region_dict)} 个")
    print(f"✅ Types 索引: {len(aligner.type_dict)} 个")
    
    assert len(aligner.all_points) == 40, f"预期 40 个点位 (4 areas + 36 regions), 实际 {len(aligner.all_points)}"
    assert aligner.kdtree_available == True, "scipy 已安装，KD-Tree 应可用"
    
    print("\n✅ 初始化测试通过")
    return True


def test_find_nearest():
    """测试 find_nearest 方法"""
    print("\n" + "=" * 60)
    print("测试 3: find_nearest")
    print("=" * 60)
    
    aligner = CoordAligner()
    
    # 测试 1: 地图中心点
    test_x, test_y = 2048, 2048
    results = aligner.find_nearest(test_x, test_y, count=5)
    
    print(f"\n查询点: ({test_x}, {test_y})")
    print(f"返回结果数: {len(results)}")
    
    assert len(results) <= 5, "返回结果数应 ≤ count"
    assert len(results) > 0, "应返回至少 1 个结果"
    
    # 验证返回格式
    for point, dist in results:
        assert 'pixel_x' in point, "返回的点位应包含 pixel_x"
        assert 'pixel_y' in point, "返回的点位应包含 pixel_y"
        assert dist >= 0, "距离应 ≥ 0"
        print(f"  - {point.get('title', 'N/A')}: {dist:.2f}px")
    
    # 测试 2: 带 max_distance 限制
    results_limited = aligner.find_nearest(test_x, test_y, max_distance=500, count=5)
    print(f"\n带距离限制 (500px): {len(results_limited)} 个结果")
    
    for point, dist in results_limited:
        assert dist <= 500, f"距离 {dist} 应 ≤ 500"
    
    # 测试 3: 验证排序（距离应递增）
    distances = [dist for _, dist in results]
    assert distances == sorted(distances), "结果应按距离升序排列"
    
    print("\n✅ find_nearest 测试通过")
    return True


def test_get_area_info():
    """测试 get_area_info 方法"""
    print("\n" + "=" * 60)
    print("测试 4: get_area_info")
    print("=" * 60)
    
    aligner = CoordAligner()
    
    # 测试 1: 地图中心点
    test_x, test_y = 2048, 2048
    result = aligner.get_area_info(test_x, test_y)
    
    print(f"\n查询点: ({test_x}, {test_y})")
    print(f"最近 Area: {result['area']['title'] if result['area'] else 'None'}")
    print(f"距离: {result['distance']:.2f}px")
    
    assert result['area'] is not None, "应返回最近的 area"
    assert result['distance'] >= 0, "距离应 ≥ 0"
    
    # 测试 2: 精确匹配某个 area 的坐标
    if aligner.areas:
        area = aligner.areas[0]
        px = area['pixel_x']
        py = area['pixel_y']
        
        result_exact = aligner.get_area_info(px, py)
        print(f"\n精确查询点: ({px}, {py})")
        print(f"最近 Area: {result_exact['area']['title'] if result_exact['area'] else 'None'}")
        print(f"距离: {result_exact['distance']:.2f}px")
        
        # 距离应该很小（可能是 0 或很小的值）
        assert result_exact['distance'] < 1.0, "精确坐标的距离应非常小"
    
    print("\n✅ get_area_info 测试通过")
    return True


def test_find_by_region():
    """测试 find_by_region 方法"""
    print("\n" + "=" * 60)
    print("测试 5: find_by_region")
    print("=" * 60)
    
    aligner = CoordAligner()
    
    # 测试存在的 region_id
    if aligner.regions:
        test_region_id = aligner.regions[0]['id']
        result = aligner.find_by_region(test_region_id)
        
        print(f"\nRegion ID: {test_region_id}")
        print(f"Region: {result['region']['title'] if result['region'] else 'None'}")
        print(f"Types 数量: {len(result['types'])}")
        print(f"Area: {result['area']['title'] if result['area'] else 'None'}")
        
        assert result['region'] is not None, "应返回 region 信息"
        # 注意：types 可能为空（如果 region_ids 字段未填充）
        
        print("\n✅ find_by_region 测试通过")
        return True
    else:
        print("\n⚠️ 没有 regions 数据，跳过测试")
        return True


def test_get_nearby_types():
    """测试 get_nearby_types 方法"""
    print("\n" + "=" * 60)
    print("测试 6: get_nearby_types")
    print("=" * 60)
    
    aligner = CoordAligner()
    
    # 测试 1: 地图中心点，半径 1000px
    test_x, test_y = 2048, 2048
    results = aligner.get_nearby_types(test_x, test_y, radius=1000)
    
    print(f"\n查询点: ({test_x}, {test_y}), 半径: 1000px")
    print(f"附近类型数: {len(results)}")
    
    # 验证返回格式
    for item in results[:5]:  # 只显示前 5 个
        t = item['type']
        r = item['region']
        d = item['distance']
        print(f"  - {t.get('title', 'N/A')} @ {r.get('title', 'N/A')}: {d:.2f}px")
    
    # 验证排序（距离应递增）
    if len(results) > 1:
        distances = [item['distance'] for item in results]
        assert distances == sorted(distances), "结果应按距离升序排列"
    
    # 测试 2: 验证半径限制
    for item in results:
        assert item['distance'] <= 1000, f"距离 {item['distance']} 应 ≤ 1000"
    
    print("\n✅ get_nearby_types 测试通过")
    return True


def test_get_route_info():
    """测试 get_route_info 方法"""
    print("\n" + "=" * 60)
    print("测试 7: get_route_info")
    print("=" * 60)
    
    aligner = CoordAligner()
    
    # 测试存在的 region_ids
    if len(aligner.regions) >= 3:
        test_region_ids = [r['id'] for r in aligner.regions[:3]]
        result = aligner.get_route_info(test_region_ids)
        
        print(f"\nRoute Region IDs: {test_region_ids}")
        print(f"Regions 数量: {len(result['regions'])}")
        print(f"Types 数量: {len(result['types'])}")
        print(f"Type Groups 数量: {len(result['type_groups'])}")
        print(f"Icons 数量: {len(result['icons'])}")
        
        assert len(result['regions']) == 3, "应返回 3 个 regions"
        
        print("\n✅ get_route_info 测试通过")
        return True
    else:
        print("\n⚠️ regions 数据不足，跳过测试")
        return True


def test_pixel_distance():
    """测试 pixel_distance 函数"""
    print("\n" + "=" * 60)
    print("测试 8: pixel_distance")
    print("=" * 60)
    
    # 测试 1: 相同点
    dist = pixel_distance(0, 0, 0, 0)
    assert dist == 0, "相同点的距离应为 0"
    print(f"\n(0, 0) -> (0, 0): {dist}px ✅")
    
    # 测试 2: 水平距离
    dist = pixel_distance(0, 0, 100, 0)
    assert dist == 100, "水平距离应为 100"
    print(f"(0, 0) -> (100, 0): {dist}px ✅")
    
    # 测试 3: 垂直距离
    dist = pixel_distance(0, 0, 0, 100)
    assert dist == 100, "垂直距离应为 100"
    print(f"(0, 0) -> (0, 100): {dist}px ✅")
    
    # 测试 4: 对角线距离
    dist = pixel_distance(0, 0, 100, 100)
    expected = 100 * (2 ** 0.5)
    assert abs(dist - expected) < 0.001, f"对角线距离应为 {expected}"
    print(f"(0, 0) -> (100, 100): {dist:.2f}px ✅")
    
    print("\n✅ pixel_distance 测试通过")
    return True


def test_kdtree_vs_bruteforce():
    """测试 KD-Tree 和暴力搜索结果一致性"""
    print("\n" + "=" * 60)
    print("测试 9: KD-Tree vs 暴力搜索")
    print("=" * 60)
    
    aligner = CoordAligner()
    
    # 临时禁用 KD-Tree
    aligner.kdtree_available = False
    aligner.kdtree = None
    
    test_x, test_y = 2048, 2048
    
    # 暴力搜索结果
    results_brute = aligner.find_nearest(test_x, test_y, count=10)
    
    # 恢复 KD-Tree
    aligner.kdtree_available = True
    from scipy.spatial import KDTree
    coords = [[p['pixel_x'], p['pixel_y']] for p in aligner.all_points]
    aligner.kdtree = KDTree(coords)
    
    # KD-Tree 结果
    results_kdtree = aligner.find_nearest(test_x, test_y, count=10)
    
    # 比较结果（允许顺序不同）
    dists_brute = sorted([d for _, d in results_brute])
    dists_kdtree = sorted([d for _, d in results_kdtree])
    
    print(f"\n暴力搜索前 5 个距离: {[f'{d:.2f}' for d in dists_brute[:5]]}")
    print(f"KD-Tree 前 5 个距离: {[f'{d:.2f}' for d in dists_kdtree[:5]]}")
    
    # 验证距离一致（允许微小浮点误差）
    for d1, d2 in zip(dists_brute, dists_kdtree):
        assert abs(d1 - d2) < 0.001, f"距离不一致: {d1} vs {d2}"
    
    print("\n✅ KD-Tree 和暴力搜索结果一致")
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("坐标对齐引擎 - 端到端测试")
    print("=" * 60)
    
    tests = [
        ("数据加载", test_load_points),
        ("CoordAligner 初始化", test_coord_aligner_init),
        ("find_nearest", test_find_nearest),
        ("get_area_info", test_get_area_info),
        ("find_by_region", test_find_by_region),
        ("get_nearby_types", test_get_nearby_types),
        ("get_route_info", test_get_route_info),
        ("pixel_distance", test_pixel_distance),
        ("KD-Tree vs 暴力搜索", test_kdtree_vs_bruteforce),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            success = test_func()
            if success:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ 测试失败: {name}")
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📊 总计: {passed + failed}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
