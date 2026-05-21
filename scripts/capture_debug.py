import win32gui
import win32ui
import win32con
from PIL import Image

# Debug: list all visible windows with their sizes
print("=== All visible windows ===")
all_w = []
def cb1(h, lst):
    if win32gui.IsWindowVisible(h):
        t = win32gui.GetWindowText(h)
        rect = win32gui.GetWindowRect(h)
        w, h = rect[2]-rect[0], rect[3]-rect[1]
        if w > 100:
            lst.append((h, t, w, h))
            print(f'  [{h}] "{t}" {w}x{h}')
win32gui.EnumWindows(cb1, all_w)

print("\n=== Looking for Roco windows ===")
targets = []
for h, t, w, hh in all_w:
    if 'Roco Go' in t or 'Roco' in t:
        targets.append((h, 'main'))
        print(f"  Found main: hwnd={h}")
    elif (w == 240 and hh == 240) or ('python' in t.lower() and w <= 260 and hh <= 260):
        targets.append((h, 'hud'))
        print(f"  Found HUD: hwnd={h} ({t})")

if not targets:
    print("  No targets found!")

base = r'D:\Roco_Navigation_Tool_Workspace'
for hwnd, name in targets:
    try:
        rect = win32gui.GetWindowRect(hwnd)
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        print(f"\nCapturing {name}: hwnd={hwnd} rect={rect} size={w}x{h}")
        
        hwndDC = win32gui.GetDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(bitmap)
        result = saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)
        print(f"  BitBlt result: {result}")
        
        bmpinfo = bitmap.GetInfo()
        bmpstr = bitmap.GetBitmapBits(True)
        img = Image.frombuffer('RGB', (w, h), bmpstr, 'raw', 'BGRX', 0, 1)
        path = f'{base}\\_screen_{name}.png'
        img.save(path)
        print(f"  Saved: {path}")
        
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        win32gui.DeleteObject(bitmap.GetHandle())
    except Exception as e:
        print(f"  Error capturing {name}: {e}")