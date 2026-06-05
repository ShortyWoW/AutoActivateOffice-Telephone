import os
import re
from PIL import Image, ImageGrab, ImageTk
import tkinter as tk
from src.logging_setup import logger
from src.config import TESSERACT_SEARCH_PATHS, DIGITS_ONLY_RE, IID_TOTAL_DIGITS, IID_GROUPS, IID_DIGITS_PER_GROUP

# Lazy load heavy dependencies to speed up application startup
np = None
cv2 = None
pytesseract = None

def _init_ocr_dependencies():
    global np, cv2, pytesseract
    if pytesseract is None:
        logger.info("Lazy-loading heavy OCR dependencies (numpy, cv2, pytesseract)...")
        import numpy as _np
        import cv2 as _cv2
        import pytesseract as _pytesseract
        np = _np
        cv2 = _cv2
        pytesseract = _pytesseract

# Initialize Tesseract executable path
tesseract_initialized = False

def init_tesseract():
    """
    Searches for the Tesseract OCR binary in configured search paths
    and registers it with pytesseract.
    """
    _init_ocr_dependencies()
    global tesseract_initialized
    if tesseract_initialized:
        return True

    # First check if standard system-installed tesseract is in PATH
    try:
        # Pytesseract check
        pytesseract.get_tesseract_version()
        logger.info("Tesseract is available via system PATH.")
        tesseract_initialized = True
        return True
    except Exception:
        pass

    # Search in custom paths
    logger.info("Searching for Tesseract binary in local and system paths...")
    for path in TESSERACT_SEARCH_PATHS:
        logger.info(f"Checking path: {path}")
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Tesseract binary found and registered: {path}")
            tesseract_initialized = True
            return True
            
    logger.warning("Tesseract binary was not found in checked paths.")
    return False

class ScreenSniper:
    """
    A full-screen overlay that allows the user to click and drag
    to select a region of the screen for OCR processing.
    """
    def __init__(self, root, callback):
        self.root = root
        self.callback = callback
        
        # Hide the main window
        self.root.withdraw()
        # Wait briefly for main window to hide before taking screenshot
        self.root.after(300, self.start_snipping)
        
    def start_snipping(self):
        try:
            # Grab screenshot of primary display
            self.screenshot = ImageGrab.grab()
        except Exception as e:
            logger.error(f"Failed to grab screenshot: {e}")
            self.root.deiconify()
            self.callback(None)
            return
            
        # Create borderless top-level window
        self.sniper_win = tk.Toplevel(self.root)
        self.sniper_win.attributes("-fullscreen", True)
        self.sniper_win.attributes("-topmost", True)
        self.sniper_win.config(cursor="cross")
        
        # Create canvas for drawing selection rectangle
        self.canvas = tk.Canvas(self.sniper_win, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Render screenshot on canvas
        self.tk_image = ImageTk.PhotoImage(self.screenshot)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        
        # Add visual instruction banner
        self.canvas.create_text(
            self.screenshot.width // 2, 40,
            text="DRAG A BOX OVER THE INSTALLATION ID - PRESS ESC TO CANCEL",
            fill="red", font=("Segoe UI", 16, "bold")
        )
        
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        
        # Bind events
        self.sniper_win.bind("<ButtonPress-1>", self.on_press)
        self.sniper_win.bind("<B1-Motion>", self.on_drag)
        self.sniper_win.bind("<ButtonRelease-1>", self.on_release)
        self.sniper_win.bind("<Escape>", self.on_cancel)
        
    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="red", width=2
        )
        
    def on_drag(self, event):
        cur_x, cur_y = event.x, event.y
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)
        
    def on_release(self, event):
        end_x, end_y = event.x, event.y
        
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        self.sniper_win.destroy()
        self.root.deiconify()
        
        # Minimum select check
        if (x2 - x1) > 10 and (y2 - y1) > 10:
            cropped = self.screenshot.crop((x1, y1, x2, y2))
            self.callback(cropped)
        else:
            logger.info("Selection box too small, cancel capture.")
            self.callback(None)
            
    def on_cancel(self, event):
        self.sniper_win.destroy()
        self.root.deiconify()
        self.callback(None)

def preprocess_image(pil_img: Image.Image) -> "np.ndarray":
    """
    Applies OpenCV preprocessing to optimize image quality for OCR:
    1. Grayscale
    2. Cubic Resize (2.5x scale)
    3. Bilateral filter for noise reduction
    4. Otsu's Binary Thresholding
    """
    _init_ocr_dependencies()
    # Convert PIL Image to OpenCV Grayscale
    open_cv_image = np.array(pil_img)
    if len(open_cv_image.shape) == 3:
        # Convert RGB to BGR first (since PIL is RGB and OpenCV functions expect BGR or Grayscale)
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
    else:
        gray = open_cv_image
        
    # Enlarge the image (helps OCR on low-DPI screen text)
    scale_factor = 2.5
    resized = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
    
    # Bilateral filter reduces noise while keeping edge details sharp
    filtered = cv2.bilateralFilter(resized, 9, 75, 75)
    
    # Apply Otsu's thresholding to get a crisp black-and-white output
    thresh = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    
    # In some cases, a dark background with light text might need inversion.
    # We will assume a light background by checking the mean value of the border pixels.
    # If the border is mostly black, we invert the image.
    h, w = thresh.shape
    border_pixels = np.concatenate([thresh[0, :], thresh[-1, :], thresh[:, 0], thresh[:, -1]])
    if np.mean(border_pixels) < 127:
        thresh = cv2.bitwise_not(thresh)
        
    return thresh

def perform_ocr(pil_img: Image.Image) -> list:
    """
    Preprocesses the cropped image, performs Tesseract OCR, parses
    all discovered digits, and returns groups of 7 digits.
    """
    if not init_tesseract():
        logger.error("OCR canceled: Tesseract binary is not configured.")
        return []
        
    try:
        # Preprocess the image
        processed_img = preprocess_image(pil_img)
        
        # Configure Tesseract to recognize only digits in uniform blocks
        custom_config = r'--psm 6 -c tessedit_char_whitelist=0123456789'
        
        # Run OCR
        ocr_result = pytesseract.image_to_string(processed_img, config=custom_config)
        logger.info(f"Raw OCR Output: {repr(ocr_result)}")
        
        # Extract digits
        digits = "".join(DIGITS_ONLY_RE.findall(ocr_result))
        logger.info(f"Extracted {len(digits)} digits from OCR.")
        
        return parse_iid_digits(digits)
    except Exception as e:
        logger.error(f"Error performing OCR: {e}")
        return []

def parse_iid_digits(digits_str: str) -> list:
    """
    Parses a flat string of digits into 9 groups of 7 digits.
    Returns list of 9 strings. If it can't group cleanly, returns 
    best effort groups.
    """
    # Clean the string (only digits)
    digits = "".join(DIGITS_ONLY_RE.findall(digits_str))
    
    groups = []
    # If exactly 63 digits, group them by 7
    if len(digits) == IID_TOTAL_DIGITS:
        for i in range(IID_GROUPS):
            start = i * IID_DIGITS_PER_GROUP
            end = start + IID_DIGITS_PER_GROUP
            groups.append(digits[start:end])
        logger.info("Successfully parsed exactly 63 digits into 9 groups.")
    else:
        # Best effort chunking
        logger.warning(f"Extracted {len(digits)} digits (expected {IID_TOTAL_DIGITS}). Chunking best-effort.")
        for i in range(IID_GROUPS):
            start = i * IID_DIGITS_PER_GROUP
            end = start + IID_DIGITS_PER_GROUP
            chunk = digits[start:end]
            # Pad or truncate to ensure some placeholder structure
            if len(chunk) > 0:
                groups.append(chunk.ljust(IID_DIGITS_PER_GROUP, '?')[:IID_DIGITS_PER_GROUP])
            else:
                groups.append("")
                
    return groups

def auto_detect_and_ocr() -> list:
    """
    Finds the Office Activation Wizard, focuses/restores it, takes a screenshot,
    performs OCR on the entire window, and extracts the 63 digits.
    Returns list of 9 groups of 7 digits if found, or None.
    """
    from src.office_window import find_office_wizard_windows, bring_window_to_front, capture_window_screenshot
    import time
    
    logger.info("Starting automated Office Activation Wizard window detection...")
    matches = find_office_wizard_windows()
    if not matches:
        logger.warning("No Microsoft Office Activation Wizard window was auto-detected.")
        return None
        
    # Take the first window match
    hwnd, title = matches[0]
    logger.info(f"Auto-detected Office Wizard window: '{title}' (HWND: {hwnd})")
    
    # Force focus and restore if minimized
    if not bring_window_to_front(hwnd):
        logger.warning("Failed to bring Office Wizard window to front.")
        return None
        
    # Wait a moment for window redraw
    time.sleep(0.6)
    
    # Capture screenshot of just that window
    screenshot = capture_window_screenshot(hwnd)
    if screenshot is None:
        logger.error("Failed to capture window screenshot.")
        return None
        
    if not init_tesseract():
        logger.error("OCR cannot proceed: Tesseract is not configured.")
        return None
        
    try:
        # Preprocess the entire window screenshot
        processed_img = preprocess_image(screenshot)
        
        # Perform OCR on the entire image
        custom_config = r'--psm 6 -c tessedit_char_whitelist=0123456789'
        ocr_result = pytesseract.image_to_string(processed_img, config=custom_config)
        logger.info(f"Raw auto-capture OCR output: {repr(ocr_result)}")
        
        # Clean to digits
        digits = "".join(DIGITS_ONLY_RE.findall(ocr_result))
        logger.info(f"Auto-extracted {len(digits)} digits from window OCR.")
        
        # We check if we got exactly 63 digits
        if len(digits) == IID_TOTAL_DIGITS:
            logger.info("Successfully extracted 63-digit Installation ID from window OCR!")
            return parse_iid_digits(digits)
            
        # If not 63 digits, check if we can find exactly 9 blocks of 7 digits
        # This handles cases where other random digits (page numbers, etc) are OCR'd.
        seven_digit_blocks = re.findall(r"\b\d{7}\b", ocr_result)
        if len(seven_digit_blocks) == 9:
            logger.info(f"Found exactly 9 blocks of 7 digits in OCR: {seven_digit_blocks}")
            return seven_digit_blocks
            
        logger.warning("Could not locate a clean 63-digit sequence in window OCR. Bailing to sniper fallback.")
        return None
    except Exception as e:
        logger.error(f"Error during auto-window OCR: {e}")
        return None
