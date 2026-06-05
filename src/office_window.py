import time
import win32gui
import win32con
from PIL import ImageGrab
from src.logging_setup import logger, get_window_title

def find_office_wizard_windows():
    """
    Finds open window handles and titles that match Microsoft Office Activation Wizard.
    """
    matches = []
    
    def win_enum_callback(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            title = get_window_title(hwnd)
            title_lower = title.lower()
            # Common titles: "Microsoft Office Activation Wizard", "Activation Wizard"
            if "activation wizard" in title_lower or "microsoft office" in title_lower:
                # Exclude our own tool title
                if "telephone helper" not in title_lower:
                    matches.append((hwnd, title))
        return True

    try:
        win32gui.EnumWindows(win_enum_callback, None)
    except Exception as e:
        logger.error(f"Error enumerating windows: {e}")
    
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
            
        win32gui.SetForegroundWindow(hwnd)
        logger.info(f"Brought window (HWND: {hwnd}) to front.")
        return True
    except Exception as e:
        logger.error(f"Failed to bring window to front: {e}")
        return False

def capture_window_screenshot(hwnd):
    """
    Retrieves the coordinates of the specified window and captures it as a PIL Image.
    """
    try:
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

def paste_cid_to_focused_window(cid_groups: list, delay_between_chars: float = 0.02):
    """
    Simulates typing the 8 groups of 6 digits into the active window.
    Assumes the user has focused the first input field (Group A).
    """
    import pyautogui
    # Join all groups into a single 48-digit string
    # In Office activation wizard, typing 6 digits in field A automatically tabs to B, etc.
    full_cid = "".join([str(g).strip() for g in cid_groups if g])
    
    if len(full_cid) != 48:
        logger.warning(f"Confirmation ID length is {len(full_cid)} instead of 48. Proceeding with caution.")
    
    logger.info("Starting simulation of CID keystrokes...")
    
    # We will simulate typing each digit. 
    # Because Office input fields auto-advance, typing sequentially works perfectly.
    for char in full_cid:
        pyautogui.write(char)
        time.sleep(delay_between_chars)
        
    logger.info("Finished typing Confirmation ID.")
    return True

def auto_paste_confirmation_id(cid_groups: list) -> bool:
    """
    Finds the Office Activation Wizard, brings it to front, and types the CID.
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
        # Paste the CID
        return paste_cid_to_focused_window(cid_groups)
    
    return False
