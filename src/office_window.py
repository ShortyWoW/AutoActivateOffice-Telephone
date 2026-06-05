import time
import win32gui
import win32con
import win32process
import os
import ctypes
from ctypes import wintypes
from PIL import ImageGrab
from src.logging_setup import logger, get_window_title

_focus_callback = None

def register_focus_callback(callback):
    """
    Registers a callback to handle focusing local process windows safely from the GUI thread.
    """
    global _focus_callback
    _focus_callback = callback

def get_extended_frame_bounds(hwnd):
    """
    Retrieves the exact visual bounds (excluding DWM shadows/drop borders) of a window.
    """
    try:
        rect = wintypes.RECT()
        # DWMWA_EXTENDED_FRAME_BOUNDS = 9
        hr = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect)
        )
        if hr == 0:
            return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception as e:
        logger.debug(f"DwmGetWindowAttribute failed: {e}")
    return None

def find_office_wizard_windows():
    """
    Finds open window handles and titles that match Microsoft Office Activation Wizard.
    Queries all windows to find ones containing relevant activation keywords,
    excluding our own process to prevent false-positives.
    """
    matches = []
    my_pid = os.getpid()
    
    def enum_callback(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            try:
                # Exclude our own window
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == my_pid:
                    return True
            except Exception:
                pass
                
            title = get_window_title(hwnd)
            title_lower = title.lower()
            
            # Keyword substring check
            if "activation wizard" in title_lower or ("office" in title_lower and "activation" in title_lower):
                matches.append((hwnd, title))
        return True
        
    try:
        win32gui.EnumWindows(enum_callback, None)
    except Exception as e:
        logger.error(f"Error enumerating windows for wizard: {e}")
        
    # Fallback to exact search if EnumWindows was empty but FindWindow works
    if not matches:
        for title in [
            "Microsoft Office Activation Wizard", 
            "Activation Wizard", 
            "Office Activation Wizard", 
            "Microsoft Office Activation"
        ]:
            hwnd = win32gui.FindWindow(None, title)
            if hwnd and win32gui.IsWindowVisible(hwnd):
                matches.append((hwnd, title))
                break
                
    return matches

def bring_window_to_front(hwnd):
    """
    Brings the window with specified handle to the front, restoring it if minimized.
    """
    try:
        # Check if minimized
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            
        # Avoid SetForegroundWindow deadlock if window belongs to our own process
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid != os.getpid():
            win32gui.SetForegroundWindow(hwnd)
        else:
            if _focus_callback:
                _focus_callback(hwnd)
            else:
                win32gui.SetForegroundWindow(hwnd)
            
        logger.info(f"Brought window (HWND: {hwnd}) to front.")
        return True
    except Exception as e:
        logger.error(f"Failed to bring window to front: {e}")
        return False

def capture_window_screenshot(hwnd):
    """
    Retrieves the coordinates of the specified window and captures it as a PIL Image.
    Uses true visual bounds (excluding borders/shadows) if possible.
    """
    try:
        bounds = get_extended_frame_bounds(hwnd)
        if bounds:
            x1, y1, x2, y2 = bounds
        else:
            rect = win32gui.GetWindowRect(hwnd)
            x1, y1, x2, y2 = rect
            
        width = x2 - x1
        height = y2 - y1
        if width <= 0 or height <= 0:
            logger.error("Invalid window bounds detected.")
            return None
            
        logger.info(f"Capturing window bounds: x1={x1}, y1={y1}, x2={x2}, y2={y2} (Width: {width}, Height: {height})")
        # Crop the screenshot to window bounds
        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        return screenshot
    except Exception as e:
        logger.error(f"Failed to capture window screenshot: {e}")
        return None

def paste_cid_to_focused_window(cid_groups: list, delay_between_chars: float = 0.01):
    """
    Simulates typing the 8 groups of 6 digits into the active window.
    Assumes the user has focused the first input field (Group A).
    """
    import pyautogui
    # Join all groups into a single 48-digit string
    full_cid = "".join([str(g).strip() for g in cid_groups if g])
    
    if len(full_cid) != 48:
        logger.warning(f"Confirmation ID length is {len(full_cid)} instead of 48. Proceeding with caution.")
    
    logger.info("Starting simulation of CID keystrokes...")
    
    old_pause = pyautogui.PAUSE
    pyautogui.PAUSE = 0.005
    try:
        pyautogui.write(full_cid, interval=delay_between_chars)
    finally:
        pyautogui.PAUSE = old_pause
        
    logger.info("Finished typing Confirmation ID.")
    return True

def auto_paste_confirmation_id(cid_groups: list) -> bool:
    """
    Finds the Office Activation Wizard, brings it to front, focuses Box A, and types the CID.
    If no window is found, logs a warning and returns False.
    """
    matches = find_office_wizard_windows()
    
    if not matches:
        logger.warning("Microsoft Office Activation Wizard window was not auto-detected.")
        return False
        
    # Take the first match
    hwnd, title = matches[0]
    logger.info(f"Auto-detected Office window: '{title}' (HWND: {hwnd})")
    
    if bring_window_to_front(hwnd):
        # Small delay to let window focus settle
        time.sleep(0.8)
        
        # Focus Box A by clicking it automatically
        try:
            import pyautogui
            import win32gui
            rect = win32gui.GetWindowRect(hwnd)
            x1, y1, x2, y2 = rect
            width = x2 - x1
            height = y2 - y1
            if width > 0 and height > 0:
                # Baseline coordinates for a 620x560 window layout:
                # Box A center: X = 103, Y = 344
                click_x = int(x1 + (103 * (width / 620.0)))
                click_y = int(y1 + (344 * (height / 560.0)))
                
                logger.info(f"Auto-clicking Box A at screen coordinates ({click_x}, {click_y}) to set focus...")
                old_x, old_y = pyautogui.position()
                pyautogui.click(click_x, click_y)
                pyautogui.moveTo(old_x, old_y)
                time.sleep(0.3)
        except Exception as e:
            logger.warning(f"Failed to auto-click Box A: {e}")
            
        # Paste the CID
        return paste_cid_to_focused_window(cid_groups)
    
    return False
