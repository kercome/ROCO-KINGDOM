import sys
sys.path.insert(0, r'D:\Roco_Navigation_Tool_Workspace')
from path_finder import PathFinder

pf = PathFinder(r'D:\Roco_Navigation_Tool_Workspace\aligned_points.json')
print(f'Graph nodes: {len(pf.graph)}')
total_edges = sum(len(v) for v in pf.graph.values()) // 2
print(f'Graph edges: {total_edges}')

# Test A* between two points
result = pf.a_star(500, 500, 3500, 3500)
if result:
    print(f'A* path found: {len(result["path"])} steps')
    print(f'Distance: {result["distance"]:.1f}px')
    print(f'Waypoints visited: {len(result.get("waypoints", []))}')
else:
    print('A* no path (graph may be disconnected)')

# Test navigate_from_player  
route = pf.navigate_from_player(2048, 2048)
if route:
    print(f'navigate_from_player: {len(route["path"])} steps, {route["distance"]:.1f}px')
else:
    print('navigate_from_player: no route')

print('Test PASSED')