import sys, os
sys.path.insert(0, r'D:\Roco_Navigation_Tool_Workspace')

print('=== Syntax & Import Check ===')

# AST check
import ast
with open(r'D:\Roco_Navigation_Tool_Workspace\roco_navigation_system.py', 'r', encoding='utf-8') as f:
    code = f.read()
tree = ast.parse(code)
classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
print(f'Classes: {classes}')
print(f'AST: OK ({len(code.splitlines())} lines)')

# Dependency checks
deps = {}
try:
    import PyQt5
    deps['PyQt5'] = 'OK'
except:
    deps['PyQt5'] = 'MISSING'
try:
    from PIL import Image
    deps['Pillow'] = 'OK'
except:
    deps['Pillow'] = 'MISSING'
try:
    import numpy as np
    deps['numpy'] = 'OK'
except:
    deps['numpy'] = 'MISSING'
try:
    import cv2
    deps['cv2'] = 'OK'
except:
    deps['cv2'] = 'optional'
try:
    import win32gui
    deps['win32gui'] = 'OK'
except:
    deps['win32gui'] = 'MISSING'

for k, v in deps.items():
    print(f'  {k}: {v}')

# Import test
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
try:
    from roco_navigation_system import RocoNavigationSystem, RocoOverlayHUD, MapEditorGraphicsView
    print('Import: OK')
    print('\nAll checks PASSED')
except ImportError as e:
    print(f'Import FAILED: {e}')
    import traceback; traceback.print_exc()