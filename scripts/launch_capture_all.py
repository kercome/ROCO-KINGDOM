"""一揽子：启动 Roco + 截图主窗口和 HUD"""
import subprocess, sys, os, time
import win32gui
from PIL import ImageGrab

# Kill old instances
import signal
for p in __import__('psutil').process_iter(['pid', 'name', 'cmdline']):
    try:
        if p.info['name'] == 'python.exe' and p.info.get('cmdline') and 'roco_navigation_system' in ' '.join(p.info['cmdline']):
            p.kill()
    except:
        pass
time.sleep(2)

# Launch
proc = subprocess.Popen(
    [sys.executable, '-X', 'utf8', r'D:\Roco_Navigation_Tool_Workspace\roco_navigation_system.py'],
    creationflags=subprocess.CREATE_NEW_CONSOLE
)
print(f'Launched PID: {proc.pid}')

# Wait
time.sleep(5)

# Find and capture ALL windows
base = r'D:\Roco_Navigation_Tool_Workspace'
found = []

def cb(h, ctx):
    if not win32gui.IsWindowVisible(h):
        return
    t = win32gui.GetWindowText(h)
    try:
        rect = win32gui.GetWindowRect(h)
    except:
        return
    w, hh = rect[2] - rect[0], rect[3] - rect[1]
    if w < 50 or hh < 50:
        return
    found.append((h, t, w, hh, rect))

win32gui.EnumWindows(cb, None)

for h, t, w, hh, rect in found:
    if 'Roco Go' in t:
        try:
            img = ImageGrab.grab(bbox=rect)
            img.save(os.path.join(base, '_screenshot_main.png'))
            print(f'Main captured: {w}x{hh}')
        except Exception as e:
            print(f'Main FAILED: {e}')
    elif 200 <= w <= 260 and 200 <= hh <= 260 and ('python' in t.lower() or not t.strip()):
        try:
            img = ImageGrab.grab(bbox=rect)
            img.save(os.path.join(base, '_screenshot_hud.png'))
            print(f'HUD captured: {w}x{hh}')
        except Exception as e:
            print(f'HUD FAILED: {e}')

# Also capture full screen as fallback
try:
    full = ImageGrab.grab()
    full.save(os.path.join(base, '_screenshot_fullscreen.png'))
    print(f'Full screen captured: {full.size}')
except Exception as e:
    print(f'Full screen FAILED: {e}')
