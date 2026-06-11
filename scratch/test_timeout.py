import ctypes
from ctypes import wintypes
import win32gui

def get_window_title_timeout(hwnd, timeout_ms=200) -> str:
    try:
        # Check if hung first
        if ctypes.windll.user32.IsHungAppWindow(hwnd):
            return ""
            
        WM_GETTEXT = 0x000D
        SMTO_ABORTIFHUNG = 0x0002
        
        buf = ctypes.create_unicode_buffer(512)
        result_len = ctypes.c_ulong()
        
        res = ctypes.windll.user32.SendMessageTimeoutW(
            hwnd,
            WM_GETTEXT,
            512,
            buf,  # ctypes passes buffer pointer
            SMTO_ABORTIFHUNG,
            timeout_ms,
            ctypes.byref(result_len)
        )
        if res != 0:
            return buf.value.strip()
    except Exception as e:
        print(f"Exception for HWND {hwnd}: {e}")
    return ""

def main():
    print("Testing safe window enumeration...")
    visible_windows = []
    
    def enum_win(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            title = get_window_title_timeout(hwnd)
            if title:
                visible_windows.append((hwnd, title))
        return True
        
    win32gui.EnumWindows(enum_win, None)
    print(f"Found {len(visible_windows)} visible windows:")
    for hwnd, title in visible_windows[:20]:
        print(f"HWND: {hwnd} -> Title: {repr(title)}")

if __name__ == "__main__":
    main()
