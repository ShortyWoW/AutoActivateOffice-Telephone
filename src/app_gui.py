import re
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
from src.config import (
    APP_TITLE, WINDOW_GEOMETRY, COLOR_BG, COLOR_CARD, COLOR_ACCENT, COLOR_ACCENT_HOVER,
    COLOR_TEXT, COLOR_MUTED, COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR, COLOR_BORDER,
    ICON_PATH
)
from src.logging_setup import register_gui_callback, logger
from src.clipboard_tools import copy_iid_groups, copy_cid_groups, parse_clipboard_digits
from src.ocr import ScreenSniper, perform_ocr
from src.browser_automation import BrowserController
from src.office_window import auto_paste_confirmation_id, paste_cid_to_focused_window
from src.office_wizard_simulator import OfficeWizardSimulator

class AppGui:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        
        # Set window icon
        try:
            import os
            if os.path.exists(ICON_PATH):
                self.root.iconbitmap(ICON_PATH)
            else:
                logger.debug(f"Window icon file not found at: {ICON_PATH}")
        except Exception as e:
            logger.debug(f"Failed to set window icon: {e}")
        
        # Calculate DPI scale factor dynamically
        try:
            self.scale_factor = self.root.winfo_fpixels('1i') / 96.0
        except Exception:
            self.scale_factor = 1.0
            
        logger.info(f"DPI Scale Factor detected: {self.scale_factor}")
        self.width = int(720 * self.scale_factor)
        self.collapsed_height = int(360 * self.scale_factor)
        self.expanded_height = int(680 * self.scale_factor)
        
        self.root.geometry(f"{self.width}x{self.collapsed_height}")
        self.root.configure(bg=COLOR_BG)
        
        # Enable immersive dark mode window title bar on Windows 10/11
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            # Fallback to DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
            for attr in [20, 19]:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    attr,
                    ctypes.byref(ctypes.c_int(1)),
                    ctypes.sizeof(ctypes.c_int)
                )
        except Exception as e:
            logger.debug(f"Failed to set immersive dark mode title bar: {e}")
        
        # State variables
        self.browser_controller = BrowserController()
        
        # Thread-safe message queues to decouple background threads from Tcl/Tk
        self.log_queue = queue.Queue()
        self.gui_queue = queue.Queue()
        
        # Configure root style
        self.root.option_add("*Font", "SegoeUI 10")
        
        # Build UI layout
        self.create_widgets()
        
        # Connect logger to our text box
        register_gui_callback(self.append_log)
        
        # Start queue polling loops on main thread
        self.poll_log_queue()
        self.poll_gui_queue()
        
        # Register thread-safe callback to focus local simulator window from main thread
        from src.office_window import register_focus_callback
        register_focus_callback(lambda hwnd: self.gui_queue.put(lambda: self.force_local_focus(hwnd)))
        
        logger.info("GUI Initialized.")

    def poll_log_queue(self):
        """Polls log_queue on main GUI thread and appends to GUI console widget."""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if hasattr(self, 'log_text') and self.log_text.winfo_exists():
                    self.log_text.config(state="normal")
                    self.log_text.insert(tk.END, msg)
                    self.log_text.see(tk.END)
                    self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(50, self.poll_log_queue)

    def poll_gui_queue(self):
        """Polls gui_queue on main GUI thread and executes deferred callbacks."""
        try:
            while True:
                callback = self.gui_queue.get_nowait()
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Error executing GUI callback: {e}")
        except queue.Empty:
            pass
        self.root.after(30, self.poll_gui_queue)

    def create_widgets(self):
        # 1. Header & Status Frame
        header_frame = tk.Frame(self.root, bg=COLOR_BG, pady=10)
        header_frame.pack(fill="x", padx=15)
        
        title_label = tk.Label(
            header_frame, text=APP_TITLE, fg=COLOR_TEXT, bg=COLOR_BG,
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(side="left")
        
        self.status_bar = tk.Label(
            header_frame, text="Ready", fg="white", bg=COLOR_ACCENT,
            font=("Segoe UI", 10, "bold"), padx=10, pady=4, relief="flat"
        )
        self.status_bar.pack(side="right")
        
        # Main container
        self.main_container = tk.Frame(self.root, bg=COLOR_BG)
        self.main_container.pack(fill="both", expand=True, padx=15, pady=5)
        
        # 2. Primary Action Panel (One giant Start button)
        primary_frame = tk.Frame(self.main_container, bg=COLOR_CARD, bd=1, relief="solid", pady=15)
        primary_frame.pack(fill="x", pady=5)
        
        self.btn_auto_activate = tk.Button(
            primary_frame, text="Start Auto-Activation", command=self.on_start_auto_activation,
            bg=COLOR_ACCENT, fg=COLOR_TEXT, activebackground=COLOR_ACCENT_HOVER, activeforeground="white",
            relief="flat", bd=0, padx=30, pady=12, font=("Segoe UI", 12, "bold")
        )
        self.btn_auto_activate.pack(anchor="center")
        
        # Add hover effects to the primary button
        def on_btn_enter(e):
            self.btn_auto_activate.config(bg=COLOR_ACCENT_HOVER)
        def on_btn_leave(e):
            self.btn_auto_activate.config(bg=COLOR_ACCENT)
        self.btn_auto_activate.bind("<Enter>", on_btn_enter)
        self.btn_auto_activate.bind("<Leave>", on_btn_leave)
        
        primary_desc = tk.Label(
            primary_frame, text="One-click activation: Automatically captures IID, fills browser portal, and pastes Confirmation ID.",
            fg=COLOR_MUTED, bg=COLOR_CARD, font=("Segoe UI", 9)
        )
        primary_desc.pack(anchor="center", pady=(8, 0))

        # 3. Verification Fields Panel (Compact representation of captured numbers)
        fields_card = tk.LabelFrame(
            self.main_container, text=" Verification Fields (Auto-Populated) ",
            fg=COLOR_TEXT, bg=COLOR_CARD, bd=1, relief="solid", font=("Segoe UI", 10, "bold"),
            padx=10, pady=8
        )
        fields_card.pack(fill="x", pady=5)
        
        # Row 1: IID
        iid_row = tk.Frame(fields_card, bg=COLOR_CARD)
        iid_row.pack(fill="x", pady=4)
        
        iid_lbl = tk.Label(iid_row, text="Installation ID:", fg=COLOR_TEXT, bg=COLOR_CARD, font=("Segoe UI", 9, "bold"), width=15, anchor="w")
        iid_lbl.pack(side="left")
        
        iid_fields_frame = tk.Frame(iid_row, bg=COLOR_CARD)
        iid_fields_frame.pack(side="left", fill="x", expand=True)
        
        self.iid_entries = []
        for i in range(9):
            entry = tk.Entry(
                iid_fields_frame, width=7, bg=COLOR_BG, fg=COLOR_TEXT,
                insertbackground=COLOR_TEXT, justify="center", relief="flat",
                font=("Segoe UI", 10, "bold"), highlightbackground=COLOR_BORDER,
                highlightthickness=1, highlightcolor=COLOR_ACCENT
            )
            entry.pack(side="left", padx=2, expand=True, fill="x")
            
            entry.bind("<KeyPress>", lambda e, idx=i: self.on_iid_keypress(e, idx))
            entry.bind("<KeyRelease>", lambda e, idx=i: self.on_iid_keyrelease(e, idx))
            entry.bind("<Control-v>", lambda e, idx=i: self.on_iid_paste(e, idx))
            entry.bind("<<Paste>>", lambda e, idx=i: self.on_iid_paste(e, idx))
            self.iid_entries.append(entry)
            
        # Row 2: CID
        cid_row = tk.Frame(fields_card, bg=COLOR_CARD)
        cid_row.pack(fill="x", pady=4)
        
        cid_lbl = tk.Label(cid_row, text="Confirmation ID:", fg=COLOR_TEXT, bg=COLOR_CARD, font=("Segoe UI", 9, "bold"), width=15, anchor="w")
        cid_lbl.pack(side="left")
        
        cid_fields_frame = tk.Frame(cid_row, bg=COLOR_CARD)
        cid_fields_frame.pack(side="left", fill="x", expand=True)
        
        self.cid_entries = []
        for i in range(8):
            entry = tk.Entry(
                cid_fields_frame, width=7, bg=COLOR_BG, fg=COLOR_TEXT,
                insertbackground=COLOR_TEXT, justify="center", relief="flat",
                font=("Segoe UI", 10, "bold"), highlightbackground=COLOR_BORDER,
                highlightthickness=1, highlightcolor=COLOR_ACCENT
            )
            entry.pack(side="left", padx=2, expand=True, fill="x")
            
            entry.bind("<KeyPress>", lambda e, idx=i: self.on_cid_keypress(e, idx))
            entry.bind("<KeyRelease>", lambda e, idx=i: self.on_cid_keyrelease(e, idx))
            entry.bind("<Control-v>", lambda e, idx=i: self.on_cid_paste(e, idx))
            entry.bind("<<Paste>>", lambda e, idx=i: self.on_cid_paste(e, idx))
            self.cid_entries.append(entry)

        # 4. Collapsible Manual Actions & Logs Panel
        self.manual_visible = False
        
        toggle_frame = tk.Frame(self.main_container, bg=COLOR_BG)
        toggle_frame.pack(fill="x", pady=(6, 1))
        
        self.toggle_btn = tk.Button(
            toggle_frame, text="▶ Show Advanced Controls & Log Console", command=self.toggle_manual_panel,
            fg=COLOR_MUTED, bg=COLOR_BG, relief="flat", activebackground=COLOR_BG, activeforeground=COLOR_TEXT,
            font=("Segoe UI", 9, "underline", "bold"), cursor="hand2", bd=0
        )
        self.toggle_btn.pack(side="left")
        
        self.manual_panel = tk.Frame(self.main_container, bg=COLOR_BG)
        # Packed dynamically inside toggle_manual_panel()
        
        # Sub-frame for action buttons (horizontal layout)
        buttons_frame = tk.Frame(self.manual_panel, bg=COLOR_BG)
        buttons_frame.pack(fill="x", pady=5)
        
        # Build contents inside buttons_frame
        iid_act_frame = tk.LabelFrame(
            buttons_frame, text=" Manual IID ", fg=COLOR_TEXT, bg=COLOR_CARD,
            bd=1, relief="solid", font=("Segoe UI", 9, "bold"), padx=5, pady=5
        )
        iid_act_frame.pack(side="left", fill="both", expand=True, padx=2)
        
        self.btn_capture_iid = self.create_styled_button(iid_act_frame, "Capture IID", self.on_capture_iid_clicked, COLOR_ACCENT)
        self.btn_capture_iid.pack(fill="x", pady=2)
        
        self.btn_copy_iid = self.create_styled_button(iid_act_frame, "Copy IID", self.on_copy_iid_clicked, COLOR_CARD, has_border=True)
        self.btn_copy_iid.pack(fill="x", pady=2)
        
        browser_act_frame = tk.LabelFrame(
            buttons_frame, text=" Manual Browser ", fg=COLOR_TEXT, bg=COLOR_CARD,
            bd=1, relief="solid", font=("Segoe UI", 9, "bold"), padx=5, pady=5
        )
        browser_act_frame.pack(side="left", fill="both", expand=True, padx=2)
        
        self.btn_open_web = self.create_styled_button(browser_act_frame, "Open Portal Website", self.on_open_web_clicked, COLOR_ACCENT)
        self.btn_open_web.pack(fill="x", pady=2)
        
        self.btn_fill_web = self.create_styled_button(browser_act_frame, "Fill Website Fields", self.on_fill_web_clicked, COLOR_CARD, has_border=True)
        self.btn_fill_web.pack(fill="x", pady=2)
        
        cid_act_frame = tk.LabelFrame(
            buttons_frame, text=" Manual CID & Paste ", fg=COLOR_TEXT, bg=COLOR_CARD,
            bd=1, relief="solid", font=("Segoe UI", 9, "bold"), padx=5, pady=5
        )
        cid_act_frame.pack(side="left", fill="both", expand=True, padx=2)
        
        self.btn_capture_cid = self.create_styled_button(cid_act_frame, "Scrape CID from Web", self.on_capture_cid_clicked, COLOR_ACCENT)
        self.btn_capture_cid.pack(fill="x", pady=2)
        
        self.btn_copy_cid = self.create_styled_button(cid_act_frame, "Copy CID Text", self.on_copy_cid_clicked, COLOR_CARD, has_border=True)
        self.btn_copy_cid.pack(fill="x", pady=2)
        
        self.btn_paste_office = self.create_styled_button(cid_act_frame, "Paste to Office Wizard", self.on_paste_office_clicked, COLOR_CARD, has_border=True)
        self.btn_paste_office.pack(fill="x", pady=2)
        
        # 5. Log Output Card inside manual_panel
        self.log_card_container = tk.Frame(self.manual_panel, bg=COLOR_BG)
        self.log_card_container.pack(fill="both", expand=True, pady=5)
        
        log_header_frame = tk.Frame(self.log_card_container, bg=COLOR_BG)
        log_header_frame.pack(fill="x", pady=(0, 2))
        
        log_lbl = tk.Label(log_header_frame, text="Log Console", fg=COLOR_TEXT, bg=COLOR_BG, font=("Segoe UI", 10, "bold"))
        log_lbl.pack(side="left")
        
        self.btn_launch_sim = self.create_styled_button(
            log_header_frame, "Launch Training Simulator", self.on_launch_simulator_clicked, COLOR_CARD, has_border=True
        )
        self.btn_launch_sim.pack(side="right")
        
        self.log_text = scrolledtext.ScrolledText(
            self.log_card_container, height=6, bg=COLOR_CARD, fg=COLOR_TEXT, relief="solid", bd=1,
            font=("Consolas", 9), insertbackground=COLOR_TEXT, state="disabled"
        )
        self.log_text.pack(fill="both", expand=True)

        # 6. Footer / Copyright Frame
        footer_frame = tk.Frame(self.root, bg=COLOR_BG, pady=10)
        footer_frame.pack(side="bottom", fill="x")
        
        copyright_lbl = tk.Label(
            footer_frame, text="© 2026 Nvalab.com | ", fg=COLOR_MUTED, bg=COLOR_BG, font=("Segoe UI", 9)
        )
        copyright_lbl.pack(side="left", padx=(15, 0))
        
        github_link = tk.Label(
            footer_frame, text="GitHub Repository", fg=COLOR_ACCENT, bg=COLOR_BG,
            font=("Segoe UI", 9, "underline"), cursor="hand2"
        )
        github_link.pack(side="left")
        
        import webbrowser
        github_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/ShortyWoW/AutoActivateOffice-Telephone"))
 
    def toggle_manual_panel(self):
        if self.manual_visible:
            self.manual_panel.pack_forget()
            self.toggle_btn.config(text="▶ Show Advanced Controls & Log Console")
            self.manual_visible = False
            self.root.geometry(f"{self.width}x{self.collapsed_height}")
        else:
            self.manual_panel.pack(fill="both", expand=True, pady=5)
            self.toggle_btn.config(text="▼ Hide Advanced Controls & Log Console")
            self.manual_visible = True
            self.root.geometry(f"{self.width}x{self.expanded_height}")
 
    def on_start_auto_activation(self):
        """
        Runs the full automated workflow sequence:
        1. Capture IID from Office Wizard window.
        2. Validate IID.
        3. If valid, immediately launch browser and start pipeline.
        """
        logger.info("Starting automated one-click activation sequence...")
        self.on_capture_iid_clicked()

    def create_styled_button(self, parent, text, command, bg_color, has_border=False):
        """
        Creates a flat button with modern hover states.
        """
        border_thickness = 1 if has_border else 0
        btn = tk.Button(
            parent, text=text, command=command, bg=bg_color, fg=COLOR_TEXT,
            activebackground=COLOR_ACCENT_HOVER, activeforeground="white",
            relief="flat", bd=0, padx=12, pady=6, font=("Segoe UI", 9, "bold"),
            highlightbackground=COLOR_BORDER, highlightthickness=border_thickness,
            highlightcolor=COLOR_ACCENT
        )
        
        # Hover effect bindings
        def on_enter(e):
            if bg_color == COLOR_ACCENT:
                btn.config(bg=COLOR_ACCENT_HOVER)
            else:
                btn.config(bg=COLOR_BORDER)
                
        def on_leave(e):
            btn.config(bg=bg_color)
            
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn

    def update_status(self, text, state="normal"):
        """
        Updates the status bar label at the top of the GUI.
        """
        color_map = {
            "normal": COLOR_ACCENT,
            "success": COLOR_SUCCESS,
            "warning": COLOR_WARNING,
            "error": COLOR_ERROR,
            "info": "#4f5b66"
        }
        bg = color_map.get(state, COLOR_ACCENT)
        self.status_bar.config(text=text, bg=bg)

    def append_log(self, msg):
        """
        Appends a message to the bottom log terminal text widget safely from any thread.
        """
        self.log_queue.put(msg)

    def force_local_focus(self, hwnd):
        """Safely brings a local process window (e.g. simulator) to the foreground from the main thread."""
        try:
            import win32gui
            import win32con
            if win32gui.IsWindow(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.SetActiveWindow(hwnd)
                logger.info(f"Focused local window (HWND: {hwnd}) on main thread.")
                
                # If it's our simulator window, ensure the country selection has focus to match the real wizard's initial state
                if hasattr(self, 'simulator_window') and self.simulator_window and self.simulator_window.winfo_exists():
                    self.simulator_window.focus_force()
                    if hasattr(self.simulator_window, 'country_combo'):
                        self.simulator_window.country_combo.focus_set()
                        logger.info("Focused the country selection combobox in simulator.")
        except Exception as e:
            logger.error(f"Error focusing local window on main thread: {e}")

    # --- Keyboard entry handlers for IID fields ---
    
    def on_iid_keypress(self, event, index):
        if event.keysym == "BackSpace":
            val = self.iid_entries[index].get()
            if len(val) == 0 and index > 0:
                prev_entry = self.iid_entries[index-1]
                prev_entry.focus_set()
                content = prev_entry.get()
                if content:
                    prev_entry.delete(len(content)-1, tk.END)
                return "break"

    def on_iid_keyrelease(self, event, index):
        if event.keysym in ["Tab", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Left", "Right", "Up", "Down", "BackSpace"]:
            return
            
        val = self.iid_entries[index].get()
        digits = "".join(re.findall(r"\d", val))
        
        if digits != val:
            self.iid_entries[index].delete(0, tk.END)
            self.iid_entries[index].insert(0, digits)
            val = digits
            
        if len(val) >= 7:
            if len(val) > 7:
                self.iid_entries[index].delete(7, tk.END)
            if index < 8:
                self.iid_entries[index+1].focus_set()
                self.iid_entries[index+1].icursor(0)

    def on_iid_paste(self, event, index):
        try:
            text = self.root.clipboard_get()
        except Exception:
            return "break"
            
        digits = "".join(re.findall(r"\d", text))
        if not digits:
            return "break"
            
        if len(digits) >= 63:
            # Full IID paste: fill starting from the first field always
            for i in range(9):
                self.iid_entries[i].delete(0, tk.END)
                self.iid_entries[i].insert(0, digits[i*7:(i+1)*7])
            self.iid_entries[8].focus_set()
            logger.info("Pasted full 63-digit Installation ID into entry fields.")
        else:
            # Sequential paste starting from current field
            curr_idx = index
            while digits and curr_idx < 9:
                chunk = digits[:7]
                digits = digits[7:]
                self.iid_entries[curr_idx].delete(0, tk.END)
                self.iid_entries[curr_idx].insert(0, chunk)
                if len(chunk) == 7 and curr_idx < 8:
                    curr_idx += 1
                else:
                    break
            self.iid_entries[curr_idx].focus_set()
            logger.info(f"Pasted partial digits starting from field {index+1}.")
            
        return "break"

    # --- Keyboard entry handlers for CID fields ---
    
    def on_cid_keypress(self, event, index):
        if event.keysym == "BackSpace":
            val = self.cid_entries[index].get()
            if len(val) == 0 and index > 0:
                prev_entry = self.cid_entries[index-1]
                prev_entry.focus_set()
                content = prev_entry.get()
                if content:
                    prev_entry.delete(len(content)-1, tk.END)
                return "break"

    def on_cid_keyrelease(self, event, index):
        if event.keysym in ["Tab", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Left", "Right", "Up", "Down", "BackSpace"]:
            return
            
        val = self.cid_entries[index].get()
        digits = "".join(re.findall(r"\d", val))
        
        if digits != val:
            self.cid_entries[index].delete(0, tk.END)
            self.cid_entries[index].insert(0, digits)
            val = digits
            
        if len(val) >= 6:
            if len(val) > 6:
                self.cid_entries[index].delete(6, tk.END)
            if index < 7:
                self.cid_entries[index+1].focus_set()
                self.cid_entries[index+1].icursor(0)

    def on_cid_paste(self, event, index):
        try:
            text = self.root.clipboard_get()
        except Exception:
            return "break"
            
        digits = "".join(re.findall(r"\d", text))
        if not digits:
            return "break"
            
        if len(digits) >= 48:
            # Full CID paste: fill starting from field A
            for i in range(8):
                self.cid_entries[i].delete(0, tk.END)
                self.cid_entries[i].insert(0, digits[i*6:(i+1)*6])
            self.cid_entries[7].focus_set()
            logger.info("Pasted full 48-digit Confirmation ID into entry fields.")
        else:
            # Sequential paste starting from current field
            curr_idx = index
            while digits and curr_idx < 8:
                chunk = digits[:6]
                digits = digits[6:]
                self.cid_entries[curr_idx].delete(0, tk.END)
                self.cid_entries[curr_idx].insert(0, chunk)
                if len(chunk) == 6 and curr_idx < 7:
                    curr_idx += 1
                else:
                    break
            self.cid_entries[curr_idx].focus_set()
            logger.info(f"Pasted partial Confirmation ID digits starting from field {index+1}.")
            
        return "break"

    # --- Button actions & Background threads ---
    
    def on_capture_iid_clicked(self):
        self.update_status("Auto-detecting...", "info")
        logger.info("Attempting auto-detection of Office Activation Wizard...")
        
        def auto_ocr_worker():
            try:
                from src.ocr import auto_detect_and_ocr
                groups = auto_detect_and_ocr()
                if groups:
                    # Success! Load into GUI
                    self.gui_queue.put(lambda: self.on_ocr_complete(groups))
                else:
                    # Fallback to ScreenSniper
                    self.gui_queue.put(self.fallback_to_sniper)
            except Exception as e:
                logger.error(f"Auto-detection worker crashed: {e}")
                self.gui_queue.put(self.fallback_to_sniper)
                
        threading.Thread(target=auto_ocr_worker, daemon=True).start()

    def fallback_to_sniper(self):
        logger.info("Auto-detection failed or no valid digits found. Launching manual screen capture overlay.")
        self.update_status("Select region...", "info")
        ScreenSniper(self.root, self.on_snipe_complete)

    def on_snipe_complete(self, image):
        if image is None:
            logger.info("Screen capture canceled.")
            self.update_status("Ready", "normal")
            return
            
        self.update_status("Running OCR...", "info")
        
        # Run OCR in a background thread to prevent UI freezing
        def ocr_worker():
            try:
                groups = perform_ocr(image)
                # Run updates on the GUI thread using gui_queue
                self.gui_queue.put(lambda: self.on_ocr_complete(groups))
            except Exception as e:
                logger.error(f"OCR Worker thread crashed: {e}")
                self.gui_queue.put(lambda: self.update_status("OCR Failed", "error"))
                
        threading.Thread(target=ocr_worker, daemon=True).start()

    def on_ocr_complete(self, groups):
        if not groups or all(not g for g in groups):
            self.update_status("OCR Failed", "error")
            logger.warning("No digits detected. Please make sure Tesseract is configured or try cropping again.")
            messagebox.showwarning(
                "OCR Failed",
                "Tesseract could not find digits in the cropped image.\n\n"
                "Please verify that Tesseract OCR is installed/placed in the application directory."
            )
            return
            
        # Fill entries
        for i in range(9):
            self.iid_entries[i].delete(0, tk.END)
            self.iid_entries[i].insert(0, groups[i])
            
        # Check validation
        full_digits = "".join(groups)
        if '?' in full_digits or len(full_digits) != 63:
            self.update_status("Warning: Verify IID", "warning")
            logger.warning("Installation ID was parsed with errors or missing digits. Please review fields.")
            messagebox.showwarning(
                "Verify Installation ID",
                f"Extracted {len(full_digits)} digits instead of the required 63.\n\n"
                "Some characters are marked with '?'. Please correct any OCR mistakes manually."
            )
        else:
            self.update_status("IID Captured", "success")
            logger.info("Installation ID successfully loaded and validated.")
            
            # AUTOMATION TRANSITION: Launch browser immediately on successful OCR!
            logger.info("IID captured successfully. Launching Browser activation portal automatically...")
            self.on_open_web_clicked()
            
    def get_iid_list(self) -> list:
        return [entry.get().strip() for entry in self.iid_entries]

    def get_cid_list(self) -> list:
        return [entry.get().strip() for entry in self.cid_entries]

    def on_copy_iid_clicked(self):
        groups = self.get_iid_list()
        full_iid = "".join(groups)
        if len(full_iid) != 63:
            confirm = messagebox.askyesno(
                "Incomplete IID",
                f"Your Installation ID has only {len(full_iid)} digits (should be 63).\n"
                "Do you still want to copy it to the clipboard?"
            )
            if not confirm:
                return
                
        copy_iid_groups(groups)
        self.update_status("IID Copied", "success")

    def on_open_web_clicked(self):
        self.update_status("Launching Browser...", "info")
        
        # Thread-safe read of IID on the main GUI thread before starting worker threads
        iid_list = self.get_iid_list()
        
        def launch_worker():
            try:
                success = self.browser_controller.launch()
                if success:
                    self.gui_queue.put(lambda: self.update_status("Browser Active", "success"))
                    self.gui_queue.put(lambda: logger.info("Browser session launched successfully. Please sign in manually."))
                    # Start the background pipeline monitor
                    monitor_thread = threading.Thread(
                        target=self.browser_controller.start_monitor_pipeline,
                        args=(iid_list, self.on_cid_scraped_callback),
                        daemon=True
                    )
                    monitor_thread.start()
                else:
                    self.gui_queue.put(lambda: self.update_status("Launch Failed", "error"))
                    self.gui_queue.put(lambda: messagebox.showerror(
                        "Browser Error",
                        "Failed to launch Chrome or Edge via Selenium.\n"
                        "Verify your browser is installed or try running the tool again."
                    ))
            except Exception as e:
                logger.error(f"Browser launch worker crashed: {e}", exc_info=True)
                self.gui_queue.put(lambda: self.update_status("Launch Failed", "error"))
                self.gui_queue.put(lambda: messagebox.showerror(
                    "Browser Launch Error",
                    f"An error occurred while launching browser:\n\n{e}"
                ))
                
        threading.Thread(target=launch_worker, daemon=True).start()

    def on_cid_scraped_callback(self, cid_groups):
        """
        Callback triggered when background monitor pipeline successfully scrapes CID.
        """
        def gui_update():
            for i in range(8):
                self.cid_entries[i].delete(0, tk.END)
                self.cid_entries[i].insert(0, cid_groups[i])
            self.update_status("CID Scraped", "success")
            logger.info(f"Automatically scraped Confirmation ID: {''.join(cid_groups)}")
            
            # Minimize browser window to restore focus to our application
            minimized = False
            try:
                if self.browser_controller.is_alive():
                    self.browser_controller.driver.minimize_window()
                    logger.info("Minimized browser window. Waiting for window focus to settle...")
                    minimized = True
            except Exception as e:
                logger.debug(f"Failed to minimize browser window: {e}")
                
            # If browser was minimized, wait 800ms to allow Windows window transition/focus to settle
            # otherwise focus-competition between browser minimization and wizard restoration causes lost typing focus.
            if minimized:
                self.root.after(800, self.on_paste_office_clicked)
            else:
                self.on_paste_office_clicked()
            
        self.gui_queue.put(gui_update)

    def on_fill_web_clicked(self):
        groups = self.get_iid_list()
        full_iid = "".join(groups)
        
        if not full_iid:
            messagebox.showerror("Empty IID", "Please capture or type your Installation ID before auto-filling.")
            return
            
        if not self.browser_controller.is_alive():
            messagebox.showerror("Browser Closed", "The Selenium browser is not running. Click 'Open Activation Website' first.")
            return

        self.update_status("Filling Website...", "info")
        
        def fill_worker():
            try:
                success = self.browser_controller.fill_installation_id(groups)
                if success:
                    self.gui_queue.put(lambda: self.update_status("IID Filled", "success"))
                else:
                    # Copy to clipboard fallback
                    copy_iid_groups(groups)
                    self.gui_queue.put(lambda: self.update_status("Manual Paste Req.", "warning"))
                    self.gui_queue.put(lambda: messagebox.showinfo(
                        "Manual Paste Required",
                        "The automation could not locate the Installation ID input fields on this page.\n\n"
                        "Fallback triggered: The Installation ID has been COPIED to your clipboard.\n"
                        "Please paste it manually into the website fields."
                    ))
            except Exception as e:
                logger.error(f"Fill IID worker crashed: {e}", exc_info=True)
                self.gui_queue.put(lambda: self.update_status("Fill Failed", "error"))
                
        threading.Thread(target=fill_worker, daemon=True).start()

    def on_capture_cid_clicked(self):
        # 1. First try browser scraping if browser is alive
        if self.browser_controller.is_alive():
            self.update_status("Scraping Browser...", "info")
            logger.info("Attempting to scrape Confirmation ID from browser page...")
            
            # Scrape in thread
            def scrape_worker():
                try:
                    cid_groups = self.browser_controller.scrape_confirmation_id()
                    self.gui_queue.put(lambda: self.on_scrape_finish(cid_groups))
                except Exception as e:
                    logger.error(f"Scrape CID worker crashed: {e}", exc_info=True)
                    self.gui_queue.put(lambda: self.update_status("Scrape Failed", "error"))
                    
            threading.Thread(target=scrape_worker, daemon=True).start()
            return

        # 2. Fallback: Parse clipboard
        self.update_status("Parsing Clipboard...", "info")
        logger.info("Browser not active. Attempting to parse Confirmation ID from clipboard...")
        
        digits = parse_clipboard_digits()
        if len(digits) == 48:
            cid_groups = [digits[i*6:(i+1)*6] for i in range(8)]
            self.on_scrape_finish(cid_groups)
        else:
            self.update_status("No CID Found", "warning")
            logger.warning("Could not locate a valid Confirmation ID (need 48 digits) in active browser or clipboard.")
            messagebox.showinfo(
                "CID Not Found",
                "Could not find the Confirmation ID automatically.\n\n"
                "Make sure you are on the confirmation page of the portal, or "
                "manually copy the CID text to your clipboard first, then click this button again."
            )

    def on_scrape_finish(self, cid_groups):
        if not cid_groups or len(cid_groups) != 8:
            # Retry fallback if scraper failed but clipboard might have it
            digits = parse_clipboard_digits()
            if len(digits) == 48:
                cid_groups = [digits[i*6:(i+1)*6] for i in range(8)]
            else:
                self.update_status("Scrape Failed", "warning")
                messagebox.showwarning(
                    "CID Scrape Failed",
                    "Could not extract Confirmation ID from the webpage.\n\n"
                    "Please copy the CID from the page to your clipboard, or type it manually."
                )
                return
                
        for i in range(8):
            self.cid_entries[i].delete(0, tk.END)
            self.cid_entries[i].insert(0, cid_groups[i])
            
        self.update_status("CID Captured", "success")
        logger.info("Confirmation ID successfully loaded.")

    def on_copy_cid_clicked(self):
        groups = self.get_cid_list()
        full_cid = "".join(groups)
        if len(full_cid) != 48:
            confirm = messagebox.askyesno(
                "Incomplete CID",
                f"Your Confirmation ID has only {len(full_cid)} digits (should be 48).\n"
                "Do you still want to copy it to the clipboard?"
            )
            if not confirm:
                return
                
        copy_cid_groups(groups)
        self.update_status("CID Copied", "success")

    def on_paste_office_clicked(self):
        groups = self.get_cid_list()
        full_cid = "".join(groups)
        
        if len(full_cid) != 48:
            messagebox.showerror(
                "Invalid CID",
                f"Confirmation ID must be exactly 48 digits (8 groups of 6).\n"
                f"Current length is {len(full_cid)} digits."
            )
            return

        self.update_status("Pasting to Office...", "info")
        
        def paste_worker():
            try:
                pasted, verified = auto_paste_confirmation_id(groups)
                if pasted:
                    if verified:
                        self.gui_queue.put(lambda: self.show_success_page(groups))
                    else:
                        self.gui_queue.put(lambda: self.update_status("Pasted (Unverified)", "warning"))
                        self.gui_queue.put(lambda: logger.info("Pasted Confirmation ID, but could not verify activation success via OCR."))
                else:
                    self.gui_queue.put(lambda: self.update_status("Paste Failed", "warning"))
                    self.gui_queue.put(lambda: self.prompt_manual_paste(groups))
            except Exception as e:
                import pyautogui
                if isinstance(e, pyautogui.FailSafeException):
                    logger.warning("Keystroke simulation aborted: PyAutoGUI Failsafe triggered by mouse movement.")
                    self.gui_queue.put(lambda: self.update_status("Paste Aborted", "warning"))
                    self.gui_queue.put(lambda: messagebox.showwarning(
                        "Paste Aborted",
                        "Pasting was aborted because the mouse was moved to the corner of the screen (Failsafe)."
                    ))
                else:
                    logger.error(f"Paste worker crashed: {e}", exc_info=True)
                    self.gui_queue.put(lambda: self.update_status("Paste Failed", "error"))
                
        threading.Thread(target=paste_worker, daemon=True).start()

    def prompt_manual_paste(self, groups):
        # Fallback prompts if window bringing/finding failed
        logger.warning("Could not auto-detect Office Activation Wizard window. Triggering fallback countdown.")
        
        # We will create a small countdown window letting the user focus the window manually!
        countdown_win = tk.Toplevel(self.root)
        countdown_win.title("Manual Focus Paste")
        # Scale geometry by the scale factor
        scaled_w = int(380 * self.scale_factor)
        scaled_h = int(180 * self.scale_factor)
        countdown_win.geometry(f"{scaled_w}x{scaled_h}")
        countdown_win.configure(bg=COLOR_CARD)
        countdown_win.attributes("-topmost", True)
        
        lbl = tk.Label(
            countdown_win, 
            text="Office Wizard not detected.\n\n"
                 "Please click inside box 'A' of the Office Wizard now!\n"
                 "Pasting will start in:",
            fg=COLOR_TEXT, bg=COLOR_CARD, font=("Segoe UI", 10, "bold")
        )
        lbl.pack(pady=10)
        
        count_lbl = tk.Label(countdown_win, text="5", fg=COLOR_ERROR, bg=COLOR_CARD, font=("Segoe UI", 24, "bold"))
        count_lbl.pack()
        
        def tick(sec):
            if not countdown_win.winfo_exists():
                return
            if sec > 0:
                count_lbl.config(text=str(sec))
                self.root.after(1000, lambda: tick(sec - 1))
            else:
                countdown_win.destroy()
                
                # Run the typing sequence in a worker thread to keep UI interactive
                def manual_paste_worker():
                    try:
                        paste_cid_to_focused_window(groups)
                        self.gui_queue.put(lambda: self.update_status("Pasted (Focused)", "success"))
                        
                        import win32gui
                        from src.office_window import find_office_wizard_windows, verify_and_complete_activation
                        hwnd = win32gui.GetForegroundWindow()
                        office_windows = find_office_wizard_windows()
                        office_hwnds = [w[0] for w in office_windows]
                        if hwnd in office_hwnds:
                            logger.info(f"Active window HWND {hwnd} matches Office Wizard. Running verification...")
                            verified = verify_and_complete_activation(hwnd)
                            if verified:
                                self.gui_queue.put(lambda: self.show_success_page(groups))
                    except Exception as ex:
                        logger.error(f"Manual paste worker crashed: {ex}", exc_info=True)
                        
                threading.Thread(target=manual_paste_worker, daemon=True).start()
                
        self.root.after(1000, lambda: tick(4))

    def show_success_page(self, cid_groups):
        """
        Hides the main container and shows a beautifully styled Success Page.
        """
        self.update_status("Office Activated", "success")
        logger.info("Office Activation verified via OCR. Displaying Success Page...")
        
        # Hide main widgets container
        self.main_container.pack_forget()
        
        # Create Success Frame if it doesn't exist, or recreate it
        if hasattr(self, 'success_frame') and self.success_frame.winfo_exists():
            self.success_frame.destroy()
            
        self.success_frame = tk.Frame(self.root, bg=COLOR_BG)
        self.success_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Inner Card for success details
        card = tk.Frame(self.success_frame, bg=COLOR_CARD, bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Success Icon / Graphic (glowing green circle with checkmark)
        canvas_size = int(80 * self.scale_factor)
        canvas = tk.Canvas(card, width=canvas_size, height=canvas_size, bg=COLOR_CARD, highlightthickness=0)
        canvas.pack(pady=(20, 10))
        
        # Draw checkmark circle
        r = int(35 * self.scale_factor)
        cx = canvas_size // 2
        cy = canvas_size // 2
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#1b4332", outline=COLOR_SUCCESS, width=3)
        
        # Draw checkmark lines
        canvas.create_line(
            cx - int(14 * self.scale_factor), cy + int(2 * self.scale_factor),
            cx - int(4 * self.scale_factor), cy + int(12 * self.scale_factor),
            cx + int(14 * self.scale_factor), cy - int(10 * self.scale_factor),
            fill=COLOR_SUCCESS, width=4, capstyle="round", joinstyle="round"
        )
        
        # Header text
        success_lbl = tk.Label(
            card, text="Office Activated Successfully!",
            fg=COLOR_SUCCESS, bg=COLOR_CARD, font=("Segoe UI", 16, "bold")
        )
        success_lbl.pack(pady=5)
        
        desc_lbl = tk.Label(
            card, text="The Activation Wizard has been verified and dismissed automatically.",
            fg=COLOR_TEXT, bg=COLOR_CARD, font=("Segoe UI", 10)
        )
        desc_lbl.pack(pady=(0, 15))
        
        # Divider line
        divider = tk.Frame(card, height=1, bg=COLOR_BORDER)
        divider.pack(fill="x", padx=40, pady=10)
        
        # Details Panel
        details_frame = tk.Frame(card, bg=COLOR_CARD)
        details_frame.pack(fill="x", padx=40, pady=5)
        
        # Grid layout for alignment
        details_frame.grid_columnconfigure(0, weight=1)
        details_frame.grid_columnconfigure(1, weight=3)
        
        iid_text = " ".join(self.get_iid_list())
        cid_text = " ".join(cid_groups)
        
        iid_lbl_title = tk.Label(details_frame, text="Installation ID:", fg=COLOR_MUTED, bg=COLOR_CARD, font=("Segoe UI", 9, "bold"), anchor="e")
        iid_lbl_title.grid(row=0, column=0, sticky="e", pady=4)
        iid_lbl_val = tk.Label(details_frame, text=iid_text, fg=COLOR_TEXT, bg=COLOR_CARD, font=("Consolas", 9), anchor="w", justify="left")
        iid_lbl_val.grid(row=0, column=1, sticky="w", padx=10, pady=4)
        
        cid_lbl_title = tk.Label(details_frame, text="Confirmation ID:", fg=COLOR_MUTED, bg=COLOR_CARD, font=("Segoe UI", 9, "bold"), anchor="e")
        cid_lbl_title.grid(row=1, column=0, sticky="e", pady=4)
        cid_lbl_val = tk.Label(details_frame, text=cid_text, fg=COLOR_TEXT, bg=COLOR_CARD, font=("Consolas", 9), anchor="w", justify="left")
        cid_lbl_val.grid(row=1, column=1, sticky="w", padx=10, pady=4)
        
        # Back / Restart button
        btn_back = self.create_styled_button(
            card, "Activate Another Copy", self.hide_success_page, COLOR_ACCENT
        )
        btn_back.pack(pady=20)
        
    def hide_success_page(self):
        """
        Hides the Success Page and restores the main widgets view.
        """
        if hasattr(self, 'success_frame') and self.success_frame.winfo_exists():
            self.success_frame.pack_forget()
        
        # Restore main container
        self.main_container.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Reset entry fields for next activation
        for entry in self.iid_entries:
            entry.delete(0, tk.END)
        for entry in self.cid_entries:
            entry.delete(0, tk.END)
            
        self.update_status("Ready", "normal")
        logger.info("Returned to main activation screen. Entry fields cleared.")

    def on_launch_simulator_clicked(self):
        """
        Launches the mock Office Activation Wizard in Training/Simulator Mode.
        """
        logger.info("Launching Technician Training Simulator window...")
        self.simulator_window = OfficeWizardSimulator(self.root)
        self.simulator_window.focus_set()

    def on_closing(self):
        """
        Called when GUI window is closed. Cleans up browser resources.
        """
        try:
            self.browser_controller.close()
        except Exception:
            pass
        self.root.destroy()

