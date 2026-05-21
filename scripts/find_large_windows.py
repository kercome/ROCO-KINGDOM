import win32gui
results = []
def cb(h, lst):
    if win32gui.IsWindowVisible(h):
        t = win32gui.GetWindowText(h)
        rect = win32gui.GetWindowRect(h)
        w, h = rect[2]-rect[0], rect[3]-rect[1]
        if w > 200 and h > 200:
            lst.append((h, t, w, h, rect))
win32gui.EnumWindows(cb, results)
for r in results:
    print(f'[{r[0]}] "{r[1]}" {r[2]}x{r[3]} at ({r[4][0]},{r[4][1]})')
if not results:
    print('No large windows found')