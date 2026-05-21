import ast

path = r'D:\Roco_Navigation_Tool_Workspace\vision_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

tree = ast.parse(code)
classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]

print('Syntax: OK')
print(f'Lines: {len(code.splitlines())}')
print(f'Classes: {classes}')
print(f'Methods: {functions}')

if 'VisionEngine' in classes:
    print('\nVisionEngine class: FOUND')
    for method in ['get_current_position', 'shutdown', '__init__']:
        status = method in functions
        print(f'  {method}: {status}')
else:
    print('\nVisionEngine class: MISSING!')