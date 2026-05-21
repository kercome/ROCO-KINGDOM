import sys, os, time
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, r'D:\Roco_Navigation_Tool_Workspace')

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from roco_navigation_system import RocoNavigationSystem

app = QApplication(sys.argv)
window = RocoNavigationSystem()

print('=== Simulation Path Tracking Test ===\n')

# Start simulation
window.start_simulated_path_tracking()
print('Simulation started\n')

# Track position changes
positions = []
for i in range(40):  # 4 seconds
    app.processEvents()
    time.sleep(0.1)
    px, py = window.hud.player_x, window.hud.player_y
    positions.append((int(px), int(py)))

# Check if position actually changed
unique = len(set(positions))
print(f'Samples: {len(positions)}, Unique positions: {unique}')
print(f'Start: {positions[0]}, End: {positions[-1]}')
print(f'Sim counter: {window.sim_counter}')
print(f'Player angle: {window.hud.player_angle:.1f}')

if unique > 1:
    print('\n✅ SIMULATION: PASSED — position is moving')
else:
    print('\n❌ SIMULATION: FAILED — position not changing')

# Check log
logs = window.txt_logs.toPlainText()
sim_log = [l for l in logs.split('\n') if '仿真' in l or '仿真验证' in l or '15秒' in l]
if sim_log:
    print('\nLog entries:')
    for l in sim_log:
        print(f'  {l}')
else:
    print('\nNo simulation log entries found')

print('\n=== Test Complete ===')
