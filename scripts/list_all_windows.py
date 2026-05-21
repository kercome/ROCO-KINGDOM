import win32gui
results = []
def cb(h, lst):
    if win32gui.IsWindowVisible(h):
        t = win32gui.GetWindowText(h)
        if t.strip():
            lst.append((h, t))
win32gui.EnumWindows(cb, results)
for h, t in results:
    print(f'[{h}] {t}')