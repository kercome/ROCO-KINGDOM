import sys, os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, r'D:\Roco_Navigation_Tool_Workspace')

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

try:
    from roco_navigation_system import RocoNavigationSystem
    print('Import OK')
    
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    
    print('Creating window...')
    window = RocoNavigationSystem()
    print(f'Window created: {window.windowTitle()}')
    print(f'HUD exists: {hasattr(window, "hud")}')
    print(f'txt_logs exists: {hasattr(window, "txt_logs")}')
    print(f'map_view exists: {hasattr(window, "map_view")}')
    print(f'points_list_widget exists: {hasattr(window, "points_list_widget")}')
    print(f'content_stack count: {window.content_stack.count()}')
    
    print('ALL OK - window instantiation successful')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()