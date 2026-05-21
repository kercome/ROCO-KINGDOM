import win32gui, time
time.sleep(3)
results = []
def cb(h, lst):
    if win32gui.IsWindowVisible(h):
        t = win32gui.GetWindowText(h)
        if 'Roco' in t or '导航' in t or 'GO' in t.upper():
            rect = win32gui.GetWindowRect(h)
            w, h = rect[2]-rect[0], rect[3]-rect[1]
            lst.append((h, t, w, h))
win32gui.EnumWindows(cb, results)
if results:
    for r in results:
        print(f'FOUND: hwnd={r[0]} title="{r[1]}" size={r[2]}x{r[3]}')
else:
    print('NOT FOUND - listing recent windows:')
    all_w = []
    def cb2(h, lst):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if t.strip():
                lst.append(t[:60])
    win32gui.EnumWindows(cb2, all_w)
    for w in all_w[-10:]:
        print(f'  {w}')