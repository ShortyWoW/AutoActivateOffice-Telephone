import os
import sys
import time
import tkinter as tk
from tkinter import messagebox

# Add current path to python path to resolve local imports cleanly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logging_setup import logger, log_system_diagnostics
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

def update_splash_progress(percentage: int, message: str):
    """
    Updates the PyInstaller splash screen progress text with a custom loading bar.
    """
    try:
        import pyi_splash
        # Create a text-based progress bar (30 characters max)
        total_bars = 30
        filled_bars = int(total_bars * (percentage / 100.0))
        bar_str = "|" * filled_bars
        spaces = " " * (total_bars - filled_bars)
        progress_text = f"{message}\nLoading: [{bar_str}{spaces}] {percentage}%"
        pyi_splash.update_text(progress_text)
    except ImportError:
        pass

def main():
    update_splash_progress(10, "Initializing core system...")
    time.sleep(0.25)
    
    enable_dpi_awareness()
    update_splash_progress(35, "Configuring display adaptation...")
    logger.info("Initializing AutoActivateOffice Telephone Helper...")
    time.sleep(0.25)
    
    # Log detailed system specifications for debugging/diagnostics in a background thread
    import threading
    threading.Thread(target=log_system_diagnostics, daemon=True).start()
    
    update_splash_progress(60, "Running pre-flight environment checks...")
    # Pre-flight environment check
    check_environment()
    time.sleep(0.25)
    
    update_splash_progress(80, "Building main application GUI...")
    # Initialize Tkinter root window
    root = tk.Tk()
    time.sleep(0.25)
    
    update_splash_progress(95, "Starting interface modules...")
    time.sleep(0.15)
    
    try:
        # Launch App
        app = AppGui(root)
        
        update_splash_progress(100, "Ready!")
        time.sleep(0.10)
        
        # Close PyInstaller splash screen if it exists
        try:
            import pyi_splash
            pyi_splash.close()
        except ImportError:
            pass
            
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
