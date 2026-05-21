import win32gui
import win32ui
import win32con
from PIL import Image

def capture_window(hwnd, save_path):
    """Capture window using Win32 API"""
    rect = win32gui.GetWindowRect(hwnd)
    w, h = rect[2] - rect[0], rect[3] - rect[1]
    
    hwndDC = win32gui.GetDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(bitmap)
    
    # BitBlt
    result = saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)
    
    # Convert to PIL Image
    bmpinfo = bitmap.GetInfo()
    bmpstr = bitmap.GetBitmapBits(True)
    img = Image.frombuffer('RGB', (w, h), bmpstr, 'raw', 'BGRX', 0, 1)
    img.save(save_path)
    
    # Cleanup
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)
    win32gui.DeleteObject(bitmap.GetHandle())
    
    print(f'Saved: {save_path} ({w}x{h})')

# Find windows
targets = []
def cb(h, lst):
    if win32gui.IsWindowVisible(h):
        t = win32gui.GetWindowText(h)
        if 'Roco Go' in t:
            lst.append((h, t.replace(' ', '')[:30] + '_main.png'))
        elif t == 'python' or t == 'Python':
            rect = win32gui.GetWindowRect(h)
            w, h = rect[2]-rect[0], rect[3]-rect[1]
            if w == 240 and h == 240:
                lst.append((h, 'hud.png'))
win32gui.EnumWindows(cb, targets)

base = r'D:\Roco_Navigation_Tool_Workspace\_screen'
for hwnd, name in targets:
    capture_window(hwnd, base + name)