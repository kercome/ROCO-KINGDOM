"""
启动 Roco Navigation System 并在5秒后截图
使用 PIL.ImageGrab + mss 双路径捕获
"""
import subprocess, sys, os, time
import win32gui

# 启动主程序
proc = subprocess.Popen(
    [sys.executable, '-X', 'utf8', r'D:\Roco_Navigation_Tool_Workspace\roco_navigation_system.py'],
    creationflags=subprocess.CREATE_NEW_CONSOLE
)

# 等待窗口出现
time.sleep(5)

# 查找窗口
main_hwnd = None
hud_hwnd = None
results = []

def cb(h, lst):
    if win32gui.IsWindowVisible(h):
        t = win32gui.GetWindowText(h)
        rect = win32gui.GetWindowRect(h)
        w, h = rect[2]-rect[0], rect[3]-rect[1]
        lst.append((h, t, w, h, rect))

win32gui.EnumWindows(cb, results)

for h, t, w, h, rect in results:
    if 'Roco Go' in t:
        main_hwnd = h
        main_rect = rect
        print(f'Main: [{h}] "{t}" {w}x{h} at ({rect[0]},{rect[1]})')
    elif t == 'python' or t == 'Python':
        if 200 <= w <= 260 and 200 <= h <= 260:
            hud_hwnd = h
            hud_rect = rect
            print(f'HUD: [{h}] "{t}" {w}x{h} at ({rect[0]},{rect[1]})')

# 截图
base = r'D:\Roco_Navigation_Tool_Workspace'

if main_hwnd:
    try:
        from PIL import ImageGrab
        rect = win32gui.GetWindowRect(main_hwnd)
        img = ImageGrab.grab(bbox=rect)
        path = os.path.join(base, '_screenshot_main.png')
        img.save(path)
        print(f'Main screenshot saved: {path} ({img.size})')
    except Exception as e:
        print(f'Main screenshot failed: {e}')

if hud_hwnd:
    try:
        from PIL import ImageGrab
        rect = win32gui.GetWindowRect(hud_hwnd)
        img = ImageGrab.grab(bbox=rect)
        path = os.path.join(base, '_screenshot_hud.png')
        img.save(path)
        print(f'HUD screenshot saved: {path} ({img.size})')
    except Exception as e:
        print(f'HUD screenshot failed: {e}')

if not main_hwnd and not hud_hwnd:
    print('No Roco windows found! Listing all large windows:')
    for h, t, w, hh, rect in results:
        if w > 200 and hh > 200:
            print(f'  [{h}] "{t}" {w}x{hh}')

# 不杀进程，保留给用户查看
print('\nProcess still running. Close manually or it will persist.')
