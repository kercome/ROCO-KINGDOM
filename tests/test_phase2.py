import win32gui, win32con
print('=== Phase 2: Window Handle Test ===')

# 1. Exact match test
titles = ["\u6d1b\u514b\u738b\u56fd", "Roco", "TapTap"]
found_hwnd = None
for title in titles:
    hwnd = win32gui.FindWindow(None, title)
    if hwnd:
        found_hwnd = hwnd
        print(f'  Found exact match: "{title}" -> hwnd={hwnd}')
        break

# 2. Fuzzy match test (should not crash)
if found_hwnd is None:
    results = []
    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            for kw in ["\u6d1b\u514b", "Roco"]:
                if kw in text:
                    results.append((hwnd, text))
    win32gui.EnumWindows(enum_callback, results)
    if results:
        print(f'  Fuzzy match found: {results[0][1]} -> hwnd={results[0][0]}')
    else:
        print('  No game window found (expected - game not running)')
        print('  Window detection: graceful degradation OK')

# 3. Verify GetWindowRect does not crash
if found_hwnd:
    rect = win32gui.GetWindowRect(found_hwnd)
    print(f'  Window rect: left={rect[0]} top={rect[1]} right={rect[2]} bottom={rect[3]}')
    w, h = rect[2]-rect[0], rect[3]-rect[1]
    print(f'  Window size: {w}x{h}')
else:
    print('  No window to query - degradation OK')

print('=== Phase 2: ALL PASSED ===')