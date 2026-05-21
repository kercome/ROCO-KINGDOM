"""快速捕获 HUD 圆形雷达窗口"""
import win32gui, time
from PIL import ImageGrab

# HUD 是一个 240x240 的无边框 Qt.Tool 窗口
# 它可能在枚举时被 PyQt5 内部刷新销毁重建
# 策略：枚举一次，找到后立即截图

time.sleep(1)  # 确保窗口稳定

captured = False
def enum_and_capture(h, ctx):
    global captured
    if captured:
        return
    if not win32gui.IsWindowVisible(h):
        return
    t = win32gui.GetWindowText(h)
    rect = win32gui.GetWindowRect(h)
    w, hh = rect[2] - rect[0], rect[3] - rect[1]
    
    # HUD 特征：240x240, title="python", Qt.Tool 窗口
    if w == 240 and hh == 240:
        try:
            img = ImageGrab.grab(bbox=rect)
            path = r'D:\Roco_Navigation_Tool_Workspace\_screenshot_hud.png'
            img.save(path)
            print(f'HUD captured: hwnd={h}, title="{t}", size={w}x{hh}')
            print(f'Saved: {path}')
            captured = True
        except Exception as e:
            print(f'HUD capture failed for hwnd={h}: {e}')

win32gui.EnumWindows(enum_and_capture, None)

if not captured:
    print('HUD not captured. Trying broader search...')
    # 列出所有 200-300 范围的窗口
    def enum_broad(h, ctx):
        if not win32gui.IsWindowVisible(h):
            return
        rect = win32gui.GetWindowRect(h)
        w, hh = rect[2] - rect[0], rect[3] - rect[1]
        if 200 <= w <= 300 and 200 <= hh <= 300:
            t = win32gui.GetWindowText(h)
            print(f'  [{h}] "{t}" {w}x{hh} at ({rect[0]},{rect[1]})')
            try:
                img = ImageGrab.grab(bbox=rect)
                path = r'D:\Roco_Navigation_Tool_Workspace\_screenshot_hud.png'
                img.save(path)
                print(f'  -> Saved as fallback!')
            except:
                pass
    win32gui.EnumWindows(enum_broad, None)
