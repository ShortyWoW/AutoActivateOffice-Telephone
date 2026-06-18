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
    Uses robust Win32 techniques (attaching thread input and sending dummy keyboard events)
    to bypass OS foreground lock restrictions.
    """
    try:
        import win32api
        
        # Check if minimized
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            
        # Avoid SetForegroundWindow deadlock if window belongs to our own process
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid == os.getpid():
            if _focus_callback:
                _focus_callback(hwnd)
                logger.info(f"Focused local window (HWND: {hwnd}) via GUI focus callback.")
                return True
            
        fore_hwnd = win32gui.GetForegroundWindow()
        if fore_hwnd != hwnd:
            target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
            fore_thread, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
            curr_thread = win32api.GetCurrentThreadId()
            
            # Try Alt-key injection to bypass foreground restrictions
            try:
                ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)  # ALT down
                ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # ALT up
            except Exception as e:
                logger.debug(f"Alt-key injection failed: {e}")
                
            attached = False
            # Attach threads if they are different
            if fore_thread != curr_thread and target_thread != curr_thread:
                try:
                    win32process.AttachThreadInput(fore_thread, curr_thread, True)
                    win32process.AttachThreadInput(target_thread, curr_thread, True)
                    attached = True
                except Exception as e:
                    logger.debug(f"AttachThreadInput failed: {e}")
                    
            try:
                win32gui.SetForegroundWindow(hwnd)
                win32gui.BringWindowToTop(hwnd)
                try:
                    win32gui.SetActiveWindow(hwnd)
                except Exception:
                    pass
            finally:
                if attached:
                    try:
                        win32process.AttachThreadInput(fore_thread, curr_thread, False)
                        win32process.AttachThreadInput(target_thread, curr_thread, False)
                    except Exception:
                        pass
        else:
            # Already foreground, bring to top
            try:
                win32gui.BringWindowToTop(hwnd)
            except Exception:
                pass
            
        logger.info(f"Brought window (HWND: {hwnd}) to front.")
        return True
    except Exception as e:
        logger.error(f"Failed to bring window to front: {e}")
        # Fallback to simple ShowWindow
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.BringWindowToTop(hwnd)
            return True
        except Exception:
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

def verify_and_complete_activation(hwnd) -> bool:
    """
    After typing the Confirmation ID, submits the wizard, verifies activation via OCR,
    and closes/dismisses the window if successful.
    Returns True if activation was verified and dismissed, False otherwise.
    """
    import pyautogui
    from src.ocr import perform_text_ocr
    
    # Step 1: Wait 1 second after pasting, then press Enter
    logger.info("Waiting 1.0 second before submitting Confirmation ID...")
    time.sleep(1.0)
    logger.info("Pressing Enter to submit Confirmation ID...")
    pyautogui.press('enter')
    
    # Step 2: Wait 1.5 seconds for window transition
    logger.info("Waiting 1.5 seconds for activation screen to render...")
    time.sleep(1.5)
    
    # Step 3: Capture screenshot of the window
    screenshot = capture_window_screenshot(hwnd)
    if screenshot is None:
        logger.warning("Failed to capture window screenshot for activation verification.")
        return False
        
    # Step 4: OCR scan the window text
    logger.info("Performing OCR scan on Wizard window to verify activation status...")
    ocr_text = perform_text_ocr(screenshot)
    logger.info(f"OCR Scanned Window Text:\n{ocr_text}")
    
    # Step 5: Check if success message is found
    text_lower = ocr_text.lower()
    
    # Check for keywords indicating success
    is_success = False
    if "you have activated office" in text_lower or ("activated" in text_lower and "office" in text_lower):
        logger.info("OCR scan detected 'You have activated Office' success phrase!")
        is_success = True
    elif "activated" in text_lower:
        logger.info("OCR scan detected 'activated' success keyword. Assuming activation succeeded.")
        is_success = True
        
    if is_success:
        # Step 6: Wait 1 second, then press Enter again to close/dismiss
        logger.info("Waiting 1.0 second before dismissing the successful activation window...")
        time.sleep(1.0)
        logger.info("Pressing Enter to close/dismiss the Activation Wizard...")
        pyautogui.press('enter')
        return True
    else:
        logger.warning("Activation success text not found in OCR scan. Let technician take over.")
        return False

def auto_paste_confirmation_id(cid_groups: list) -> tuple:
    """
    Finds the Office Activation Wizard, brings it to front, focuses Box A, types the CID,
    submits it, verifies activation via OCR, and closes it if successful.
    Returns a tuple: (pasted_successfully, activation_verified)
    """
    matches = find_office_wizard_windows()
    
    if not matches:
        logger.warning("Microsoft Office Activation Wizard window was not auto-detected.")
        return False, False
        
    # Take the first match
    hwnd, title = matches[0]
    logger.info(f"Auto-detected Office window: '{title}' (HWND: {hwnd})")
    
    if bring_window_to_front(hwnd):
        # Wait 1.5 seconds to let window focus settle completely
        time.sleep(1.5)
        
        # Focus Box A by pressing TAB from the country dropdown
        try:
            import pyautogui
            logger.info("Sending TAB key press to navigate focus to Box A...")
            pyautogui.press('tab')
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Failed to send TAB key press: {e}")
            
        # Paste the CID
        pasted = paste_cid_to_focused_window(cid_groups)
        if not pasted:
            return False, False
            
        # Verify and complete the activation
        verified = verify_and_complete_activation(hwnd)
        return True, verified
    
    return False, False

