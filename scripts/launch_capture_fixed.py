import subprocess, sys, os, time
import win32gui
from PIL import ImageGrab

print("=== Launch & Capture (fixed) ===\n")

# 启动主程序
proc = subprocess.Popen(
    [sys.executable, '-X', 'utf8', r'D:\Roco_Navigation_Tool_Workspace\roco_navigation_system.py'],
    creationflags=subprocess.CREATE_NEW_CONSOLE
)

# 等待窗口出现
time.sleep(6)

# 查找窗口（正确处理返回值）
main_hwnd = None
hud_hwnd = None

def enum_cb(h, ctx):
    global main_hwnd, hud_hwnd
    if not win32gui.IsWindowVisible(h):
        return
    t = win32gui.GetWindowText(h)
    if not t.strip():
        return
    rect = win32gui.GetWindowRect(h)
    w, hh = rect[2] - rect[0], rect[3] - rect[1]
    if 'Roco Go' in t:
        main_hwnd = h
        print(f'Main found: hwnd={h}, title="{t[:40]}", size={w}x{hh}')
    elif w == 240 and hh == 240 and 'python' in t.lower():
        hud_hwnd = h
        print(f'HUD found: hwnd={h}, title="{t}", size={w}x{hh}')

win32gui.EnumWindows(enum_cb, None)

base = r'D:\Roco_Navigation_Tool_Workspace'

# 截图主窗口
if main_hwnd:
    try:
        rect = win32gui.GetWindowRect(main_hwnd)
        print(f'\nCapturing main window: rect={rect}')
        img = ImageGrab.grab(bbox=rect)
        path = os.path.join(base, '_screenshot_main.png')
        img.save(path)
        print(f'  Saved: {path} ({img.size})')
    except Exception as e:
        print(f'  Main capture FAILED: {e}')
else:
    print('\nMain window NOT found!')

# 截图 HUD
if hud_hwnd:
    try:
        rect = win32gui.GetWindowRect(hud_hwnd)
        print(f'\nCapturing HUD: rect={rect}')
        img = ImageGrab.grab(bbox=rect)
        path = os.path.join(base, '_screenshot_hud.png')
        img.save(path)
        print(f'  Saved: {path} ({img.size})')
    except Exception as e:
        print(f'  HUD capture FAILED: {e}')
else:
    print('\nHUD window NOT found!')

print('\nProcess still running. Close manually.')
