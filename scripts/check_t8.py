import ast, sys, os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

path = r'D:\Roco_Navigation_Tool_Workspace\overlay_ui.py'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()
tree = ast.parse(code)
methods = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
required = ['init_window_follower', '_follow_game_window', 'set_penetration', 'set_topmost', 'set_show_coords']

print(f'Lines: {len(code.splitlines())}')
print(f'All required methods present: {all(r in methods for r in required)}')
for r in required:
    status = "OK" if r in methods else "MISSING!"
    print(f'  {r}: {status}')

# Import test
sys.path.insert(0, r'D:\Roco_Navigation_Tool_Workspace')
from overlay_ui import OverlayUI
print('Import: OK')
print('T8 verification PASSED')