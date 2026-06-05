import logging
import os
import sys
import socket
from datetime import datetime
from src.config import LOGS_DIR

class GuiLogHandler(logging.Handler):
    """
    A custom logging handler that routes messages to a registered callback
    function (typically in the Tkinter GUI thread).
    """
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        try:
            msg = self.format(record)
            # Call the callback safely
            self.callback(msg + "\n")
        except Exception:
            self.handleError(record)

def setup_logger():
    """
    Initializes system logging. Logs are written to both standard console
    and dynamically to Logs/<SYSTEM_NAME>/<DATESTAMP>.log in the project directory.
    """
    # Get hostname and date stamp dynamically at runtime
    try:
        system_name = socket.gethostname()
    except Exception:
        system_name = os.environ.get("COMPUTERNAME", "UNKNOWN_SYSTEM")
        
    date_stamp = datetime.now().strftime("%Y-%m-%d")
    
    # Target directory: BASE_DIR/Logs/SYSTEM_NAME/
    system_log_dir = os.path.join(LOGS_DIR, system_name)
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(system_log_dir):
        try:
            os.makedirs(system_log_dir)
        except Exception as e:
            print(f"Error creating logs directory {system_log_dir}: {e}", file=sys.stderr)

    logger = logging.getLogger("AutoActivateOffice")
    logger.setLevel(logging.INFO)

    # Clear existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # File Handler
    try:
        log_file_path = os.path.join(system_log_dir, f"{date_stamp}.log")
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to create log file: {e}", file=sys.stderr)

    # Console Handler (Standard Output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("Logger initialized successfully.")
    return logger

# Global logger instance
logger = setup_logger()

def register_gui_callback(callback):
    """
    Registers a Tkinter text box callback to print logging output dynamically.
    """
    gui_handler = GuiLogHandler(callback)
    formatter = logging.Formatter('%(asctime)s: %(message)s', datefmt='%H:%M:%S')
    gui_handler.setFormatter(formatter)
    gui_handler.setLevel(logging.INFO)
    logger.addHandler(gui_handler)
    logger.info("GUI Logging connection established.")
