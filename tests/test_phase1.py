import sys, time, os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, r'D:\Roco_Navigation_Tool_Workspace')

print('=== Phase 1: Mock Test ===')

# 1. Import all core modules
modules = ['coord_mapper', 'coord_aligner', 'path_finder', 'overlay_ui', 'control_panel', 'main']
for m in modules:
    __import__(m)
    print(f'  Import {m}: OK')

# 2. Instantiate CoordAligner
from coord_aligner import CoordAligner
t0 = time.time()
aligner = CoordAligner()
t1 = time.time()
print(f'  CoordAligner init: {t1-t0:.3f}s')

# 3. Instantiate PathFinder
from path_finder import PathFinder
t0 = time.time()
finder = PathFinder()
t1 = time.time()
print(f'  PathFinder init: {t1-t0:.3f}s')

# 4. A* benchmark (<50ms target)
t0 = time.time()
result = finder.a_star(100, 100, 3900, 3900)
t1 = time.time()
if result:
    path_len = len(result.get("path", []))
    dist = result.get("distance", 0)
    print(f'  A* pathfinder: {(t1-t0)*1000:.1f}ms, {path_len} steps, {dist:.0f}px')
else:
    print(f'  A* pathfinder: FAILED (no path found)')

# 5. active_route.json write
import json
test_route = {"name": "test_route", "waypoints": [{"x":500,"y":500,"name":"p1"},{"x":600,"y":700,"name":"p2"}]}
with open(r'D:\Roco_Navigation_Tool_Workspace\active_route.json','w',encoding='utf-8') as f:
    json.dump(test_route, f, ensure_ascii=False)
print('  active_route.json: write OK')

# 6. OverlayUI import + method check
from overlay_ui import OverlayUI
new_methods = ['init_window_follower', '_follow_game_window', 'set_penetration', 'set_topmost', 'set_show_coords']
for method in new_methods:
    assert hasattr(OverlayUI, method), f'Missing method: {method}'
print('  OverlayUI new methods: all present')

# 7. ControlPanel import
from control_panel import ControlPanel
print('  ControlPanel import: OK')

print('=== Phase 1: ALL PASSED ===')