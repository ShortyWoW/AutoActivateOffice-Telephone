# AutoActivateOffice Telephone Helper

A portable, technician-friendly Windows desktop tool designed to automate the repetitive parts of Microsoft Office telephone activation. It runs directly from a USB flash drive, uses OCR to read the Installation ID (IID), opens the activation portal, and helps paste the resulting Confirmation ID (CID) back into the Office Activation Wizard.

---

## 🔒 Crucial Security & Safety Rules

- **No Credential Caching**: This tool **does not** store, request, cache, or hardcode any usernames, passwords, cookies, or MFA tokens. All authentication is done manually by the technician directly within the visible browser.
- **No License Bypassing**: This tool **does not** bypass Microsoft licensing, server activation checks, or CAPTCHAs. It is purely a productivity helper for technicians who have legitimate, authorized access to the self-service portal.
- **User-in-the-Loop**: The tool will never silently run or automatically submit final activation without user confirmation.

---

## 🚀 Key Features

1. **Screen Snipping & OCR**: Drag a box over the 9-group Installation ID inside the Office Activation Wizard. The tool processes the crop through OpenCV and runs Tesseract to extract the digits.
2. **Auto-Tabbing Input Fields**: Visual input grids for both IID (9 fields of 7 digits) and CID (8 fields of 6 digits) with smart focus tabbing and backspace return behavior.
3. **Advanced Paste Parsing**: Copying a long string of numbers (e.g. from a document or portal) and pasting it into the first entry box automatically distributes the digits across all input fields.
4. **Selenium Browser Manager**: Uses built-in Selenium Manager to automatically match and fetch the correct driver for Edge or Chrome without manual driver installation.
5. **Auto-Filling**: Attempts to locate and fill the IID text inputs on the Microsoft activation site automatically, falling back to clipboard copy if the portal page layout changes.
6. **Confirmation ID Scraper**: Scrapes the activation portal page source and text using regular expressions to automatically load the A-H CID blocks.
7. **Keystroke Simulation**: Finds the Office Activation Wizard window, brings it to focus, and types the A-H confirmation digits automatically.

---

## 📋 System Requirements

- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Development**: Python 3.11+
- **Host Browser**: Microsoft Edge (default) or Google Chrome installed
- **OCR Engine**: Tesseract OCR (required for the "Capture" feature; fallback to manual input is supported)

---

## 🛠️ Project Structure

```
AutoActivateOffice-Telephone/
├── README.md                 # Project user guide
├── requirements.txt          # Python dependencies
├── build_exe.bat             # Compiles portable distribution folder
├── run_dev.bat               # Runs application in developer mode
├── src/
│   ├── main.py               # Bootstrap entry point
│   ├── app_gui.py            # Tkinter interface and tabbing logic
│   ├── ocr.py                # Snipping overlay and Tesseract parser
│   ├── browser_automation.py  # Selenium manager & browser automation
│   ├── office_window.py      # Win32 window focus & keyboard simulator
│   ├── clipboard_tools.py    # Clipboard copy/paste helper functions
│   ├── config.py             # Themes, regexes, and search paths
│   └── logging_setup.py      # Local rotation and GUI log receiver
├── assets/
│   └── README.md
├── dist/
│   └── README.md
└── logs/
    └── app.log               # Local application log (generated at run)
```

---

## 💻 Development Setup

1. **Install Python**: Make sure Python 3.11+ is installed and added to your system PATH.
2. **Launch Developer Mode**:
   Double-click `run_dev.bat` in the root folder. The script will automatically verify and install dependencies from `requirements.txt` and launch the GUI.

---

## 📦 How to Build the Portable EXE (for USB drives)

1. Double-click `build_exe.bat`.
2. PyInstaller will compile the app and output a portable folder at:
   `dist\AutoActivateOffice-Telephone\`
3. Copy the entire `AutoActivateOffice-Telephone` folder onto your technician USB flash drive. (The drive letter can change safely; the app uses relative paths).

---

## 💾 How to Add Portable OCR (Tesseract) to your USB

By default, the tool will try to locate Tesseract OCR on the host computer (`C:\Program Files\Tesseract-OCR\`). To make the OCR capture feature work completely portably without installing anything on the customer's computer:

1. Download a portable/precompiled Tesseract zip (e.g. from UB Mannheim or GitHub).
2. Extract the files and copy the entire `Tesseract-OCR` folder (containing `tesseract.exe` and `tessdata/`) into the application directory on your USB under the folder name `tesseract`.
3. The directory structure on your USB should look like this:
   ```
   AutoActivateOffice-Telephone/
   ├── AutoActivateOffice-Telephone.exe  (Main application)
   ├── tesseract/
   │   ├── tesseract.exe
   │   └── tessdata/
   ├── logs/
   └── ...
   ```
4. When launched, the tool will auto-detect the local `tesseract/tesseract.exe` path and run the OCR engine directly from the USB drive!

---

## 💡 Troubleshooting

### OCR / Capture Issues
- **"Tesseract not configured" Warning**: Make sure you have either installed Tesseract OCR on the machine or placed the portable `tesseract` binaries folder inside the app directory as shown above.
- **Incorrect Digits**: If the OCR reads a character wrong (e.g. `8` instead of `0`), simply click the corresponding field in the grid, modify the value, and the validation will update in real-time.

### Browser / Selenium Issues
- **Browser Fails to Launch**: The tool uses `Selenium Manager` to locate your system Edge or Chrome browser. Ensure Microsoft Edge or Google Chrome is installed on the computer.
- **"Fill Website" Doesn't Type Anything**: If Microsoft alters the HTML structure of the self-service portal, the auto-fill script might fail to locate the fields. If this happens, the tool will **automatically copy the IID to your clipboard** and display a pop-up advising you to paste it manually.

### Office Wizard Paste Issues
- **Wizard Not Found / Won't Paste**: The tool brings the window to the front by searching for "Activation Wizard" or "Microsoft Office" in the window title. If it can't find it, a **5-second countdown** will appear. Simply click inside box **"A"** of the Activation Wizard during the countdown, and the tool will paste the Confirmation ID.
