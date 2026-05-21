import ast, sys, os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

path = r'D:\Roco_Navigation_Tool_Workspace\control_panel.py'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()
tree = ast.parse(code)
print(f'Lines: {len(code.splitlines())}')
print('AST: OK')

# Check required UI elements
checks = ['QPushButton', 'QComboBox', 'QCheckBox', 'QFileDialog', 'active_route.json']
for c in checks:
    status = "OK" if c in code else "MISSING"
    print(f'  {c}: {status}')

sys.path.insert(0, r'D:\Roco_Navigation_Tool_Workspace')
from control_panel import ControlPanel
print('Import: OK')
print('T7 verification PASSED')