import os
import re

# App Settings
APP_TITLE = "AutoActivateOffice Telephone Helper"
WINDOW_GEOMETRY = "720x680"

import sys

# Files and Folders
if getattr(sys, 'frozen', False):
    # PyInstaller compiled executable directory
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Development source directory
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOGS_DIR = os.path.join(BASE_DIR, "Logs")

# Activation settings
ACTIVATION_URL = "https://aka.ms/aoh"

# OCR and Tesseract configuration
# Search order for tesseract binary to support portable USB setups
TESSERACT_SEARCH_PATHS = [
    # 1. Local path relative to the script/EXE (USB portable setups)
    os.path.join(BASE_DIR, "tesseract", "tesseract.exe"),
    os.path.join(BASE_DIR, "Tesseract-OCR", "tesseract.exe"),
    os.path.join(BASE_DIR, "tesseract-ocr", "tesseract.exe"),
    os.path.join(BASE_DIR, "src", "tesseract", "tesseract.exe"),
    os.path.join(BASE_DIR, "src", "Tesseract-OCR", "tesseract.exe"),
    # 2. Program files directories (host fallback)
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

# Validation rules
# Installation ID: 9 groups of 7 digits = 63 digits
IID_GROUPS = 9
IID_DIGITS_PER_GROUP = 7
IID_TOTAL_DIGITS = IID_GROUPS * IID_DIGITS_PER_GROUP

# Confirmation ID: 8 groups (A-H) of 6 digits = 48 digits
CID_GROUPS = 8
CID_DIGITS_PER_GROUP = 6
CID_TOTAL_DIGITS = CID_GROUPS * CID_DIGITS_PER_GROUP

# Regex to find any digits in text
DIGITS_ONLY_RE = re.compile(r"\d")

# Theme styling colors (Harmonious Modern dark/blue palette)
COLOR_BG = "#1e1e24"          # Deep dark charcoal
COLOR_CARD = "#2b2b36"        # Slightly lighter slate gray for cards
COLOR_ACCENT = "#007acc"      # Electric blue accent
COLOR_ACCENT_HOVER = "#005999"# Darker blue hover
COLOR_TEXT = "#e0e0e6"        # Crisp light gray text
COLOR_MUTED = "#9090a0"       # Grayed out text
COLOR_SUCCESS = "#2ea043"     # Modern green
COLOR_WARNING = "#d29922"     # Amber/yellow warning
COLOR_ERROR = "#f85149"       # Soft red error
COLOR_BORDER = "#3f3f50"      # Subtle border color
