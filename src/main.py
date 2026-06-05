import os
import sys
import tkinter as tk
from tkinter import messagebox

# Add current path to python path to resolve local imports cleanly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logging_setup import logger
from src.app_gui import AppGui

def check_environment():
    """
    Validates the local environment and directories before launching the GUI.
    """
    # Create logs directory if missing
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Logs")
    if not os.path.exists(logs_dir):
        try:
            os.makedirs(logs_dir)
        except Exception as e:
            print(f"Failed to create Logs directory: {e}", file=sys.stderr)

def enable_dpi_awareness():
    """
    Enables DPI awareness so that Win32 coordinates align perfectly
    with PIL ImageGrab screenshots, even on scaled displays (125%, 150%, etc).
    """
    import ctypes
    try:
        # Try Per-Monitor DPI Aware (Windows 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Fallback to System DPI Aware (Windows Vista+)
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def main():
    enable_dpi_awareness()
    logger.info("Initializing AutoActivateOffice Telephone Helper...")
    
    # Pre-flight environment check
    check_environment()
    
    # Initialize Tkinter root window
    root = tk.Tk()
    
    try:
        # Launch App
        app = AppGui(root)
        
        # Intercept window close to clean up background browser sessions
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        
        # Start GUI Loop
        root.mainloop()
        
    except Exception as e:
        logger.critical(f"Unhandled exception during execution: {e}", exc_info=True)
        messagebox.showerror(
            "Application Crash",
            f"An unexpected critical error occurred:\n\n{e}\n\n"
            "Please check the Logs directory for details."
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
