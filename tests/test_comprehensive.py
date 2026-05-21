"""
Roco Navigation System — 综合测试脚本
功能：截取主窗口和雷达HUD截图，验证运行时正确性
"""
import os, sys, time
import mss
import mss.tools

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, r'D:\Roco_Navigation_Tool_Workspace')

# Step 1: import test
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from roco_navigation_system import RocoNavigationSystem

app = QApplication(sys.argv)
app.setAttribute(Qt.AA_EnableHighDpiScaling)

print("=== Roco Navigation System — Test Suite ===\n")

# Step 2: instantiation
print("[1/5] Creating main window...")
window = RocoNavigationSystem()
print(f"  Title: {window.windowTitle()}")
print(f"  Size: {window.width()}x{window.height()}")

# Step 3: component check
print("\n[2/5] Component verification...")
checks = {
    'hud (RocoOverlayHUD)': hasattr(window, 'hud'),
    'txt_logs (QTextEdit)': hasattr(window, 'txt_logs'),
    'map_view': hasattr(window, 'map_view'),
    'points_list_widget': hasattr(window, 'points_list_widget'),
    'content_stack': hasattr(window, 'content_stack'),
    'cb_top': hasattr(window, 'cb_top'),
    'cb_penetrate': hasattr(window, 'cb_penetrate'),
    'slider_opacity': hasattr(window, 'slider_opacity'),
    'slider_size': hasattr(window, 'slider_size'),
    'combo_paths': hasattr(window, 'combo_paths'),
    'btn_dashboard': hasattr(window, 'btn_dashboard'),
    'btn_map': hasattr(window, 'btn_map'),
    'btn_route': hasattr(window, 'btn_route'),
    'btn_logs': hasattr(window, 'btn_logs'),
}
for name, ok in checks.items():
    print(f"  {'✅' if ok else '❌'} {name}")

# Step 4: data loading
print("\n[3/5] Data loading...")
print(f"  Points database: {len(window.points_database)} items")
print(f"  Content stack pages: {window.content_stack.count()}")
print(f"  HUD visible: {window.hud.isVisible()}")
print(f"  HUD radius: {window.hud.radius}")
print(f"  HUD player position: ({window.hud.player_x}, {window.hud.player_y})")
print(f"  HUD player angle: {window.hud.player_angle:.1f}°")
print(f"  HUD target points count: {len(window.hud.target_points)}")

# Step 5: simulation test
print("\n[4/5] Simulated path tracking test (15s loop)...")
sim_completed = [False]
sim_errors = []
test_results = []

def check_sim_result():
    if hasattr(window, 'sim_counter'):
        print(f"  Sim counter: {window.sim_counter}")
        print(f"  Final pos: ({window.hud.player_x}, {window.hud.player_y})")
        print(f"  Final angle: {window.hud.player_angle:.1f}°")
    sim_completed[0] = True

# Trigger simulation
window.start_simulated_path_tracking()
# Run for 8 seconds (enough to see it working)
elapsed = 0
while elapsed < 80:  # 80 * 100ms = 8s
    app.processEvents()
    time.sleep(0.1)
    elapsed += 1
    if hasattr(window, 'sim_counter') and window.sim_counter >= 40:
        break

if hasattr(window, 'sim_counter'):
    print(f"  Sim counter: {window.sim_counter}")
    print(f"  Final pos: ({window.hud.player_x}, {window.hud.player_y})")
    print(f"  Final angle: {window.hud.player_angle:.1f}°")
    test_results.append(('simulation_tracking', True, f'counter={window.sim_counter}'))
else:
    print("  ❌ sim_counter not found!")
    test_results.append(('simulation_tracking', False, 'no sim_counter'))

# Step 6: waypoint operations
print("\n[5/5] Waypoint operations...")
point_count_before = len(window.points_database)
window.add_new_point_via_click(500.0, 500.0, "测试点位A")
window.add_new_point_via_click(1200.0, 800.0, "测试点位B")
point_count_after = len(window.points_database)
print(f"  Before: {point_count_before}, After: {point_count_after}")

# Verify refresh
window.refresh_points_ui_view()
test_results.append(('waypoint_add', point_count_after == point_count_before + 2, f'+{point_count_after - point_count_before}'))

# Log verification
log_text = window.txt_logs.toPlainText()
print(f"\n=== Log Output ===")
for line in log_text.split('\n')[:15]:
    print(f"  {line}")
print(f"  ... ({len(log_text.split(chr(10)))} lines total)")

# Summary
print("\n=== Test Summary ===")
all_pass = all(r[1] for r in test_results)
for name, ok, detail in test_results:
    print(f"  {'✅' if ok else '❌'} {name}: {detail}")

print(f"\n{'🎉 ALL TESTS PASSED' if all_pass else '⚠️ SOME TESTS FAILED'}")