import win32gui
from mss import MSS

# Find Roco main window
hwnd_main = None
hud_hwnd = None
results = []
def cb(h, lst):
    if win32gui.IsWindowVisible(h):
        t = win32gui.GetWindowText(h)
        rect = win32gui.GetWindowRect(h)
        w, h = rect[2]-rect[0], rect[3]-rect[1]
        lst.append((h, t, w, h, rect))
win32gui.EnumWindows(cb, results)

for r in results:
    if 'Roco Go' in r[1]:
        hwnd_main = r[0]
        print(f'Main window: {r[1]} {r[2]}x{r[3]} at ({r[4][0]},{r[4][1]})')
    elif r[2] == 240 and r[3] == 240 and 'python' in r[1].lower():
        hud_hwnd = r[0]
        print(f'HUD window: {r[1]} {r[2]}x{r[3]} at ({r[4][0]},{r[4][1]})')

with MSS() as sct:
    if hwnd_main:
        rect = win32gui.GetWindowRect(hwnd_main)
        mon = {'left': rect[0], 'top': rect[1], 'width': rect[2]-rect[0], 'height': rect[3]-rect[1]}
        img = sct.grab(mon)
        img.save(r'D:\Roco_Navigation_Tool_Workspace\_screenshot_main.png')
        print(f'Saved main window screenshot')
    
    if hud_hwnd:
        rect = win32gui.GetWindowRect(hud_hwnd)
        mon = {'left': rect[0], 'top': rect[1], 'width': rect[2]-rect[0], 'height': rect[3]-rect[1]}
        img = sct.grab(mon)
        img.save(r'D:\Roco_Navigation_Tool_Workspace\_screenshot_hud.png')
        print(f'Saved HUD screenshot')