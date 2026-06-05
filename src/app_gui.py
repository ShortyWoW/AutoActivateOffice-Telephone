import re
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from src.config import (
    APP_TITLE, WINDOW_GEOMETRY, COLOR_BG, COLOR_CARD, COLOR_ACCENT, COLOR_ACCENT_HOVER,
    COLOR_TEXT, COLOR_MUTED, COLOR_SUCCESS, COLOR_WARNING, COLOR_ERROR, COLOR_BORDER
)
from src.logging_setup import register_gui_callback, logger
from src.clipboard_tools import copy_iid_groups, copy_cid_groups, parse_clipboard_digits
from src.ocr import ScreenSniper, perform_ocr
from src.browser_automation import BrowserController
from src.office_window import auto_paste_confirmation_id, paste_cid_to_focused_window

class AppGui:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(WINDOW_GEOMETRY)
        self.root.configure(bg=COLOR_BG)
        
        # State variables
        self.browser_controller = BrowserController()
        
        # Configure root style
        self.root.option_add("*Font", "SegoeUI 10")
        
        # Build UI layout
        self.create_widgets()
        
        # Connect logger to our text box
        register_gui_callback(self.append_log)
        
        logger.info("GUI Initialized.")
        
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
        
        # Main container with scrolling or grid
        main_container = tk.Frame(self.root, bg=COLOR_BG)
        main_container.pack(fill="both", expand=True, padx=15, pady=5)
        
        # 2. Card 1: Installation ID Section
        iid_card = tk.LabelFrame(
            main_container, text=" 1. Installation ID (IID) ",
            fg=COLOR_TEXT, bg=COLOR_CARD, bd=1, relief="solid", font=("Segoe UI", 11, "bold"),
            padx=10, pady=10
        )
        iid_card.pack(fill="x", pady=5)
        
        iid_desc = tk.Label(
            iid_card, text="Retrieve 9 groups of 7 digits from the Office Activation Wizard:",
            fg=COLOR_MUTED, bg=COLOR_CARD, font=("Segoe UI", 9)
        )
        iid_desc.pack(anchor="w", pady=(0, 10))
        
        # IID Fields Frame
        iid_fields_frame = tk.Frame(iid_card, bg=COLOR_CARD)
        iid_fields_frame.pack(fill="x", pady=5)
        
        self.iid_entries = []
        for i in range(9):
            # Container for entry + sub label
            field_container = tk.Frame(iid_fields_frame, bg=COLOR_CARD)
            field_container.pack(side="left", expand=True, padx=2)
            
            entry = tk.Entry(
                field_container, width=7, bg=COLOR_BG, fg=COLOR_TEXT,
                insertbackground=COLOR_TEXT, justify="center", relief="flat",
                font=("Segoe UI", 11, "bold"), highlightbackground=COLOR_BORDER,
                highlightthickness=1, highlightcolor=COLOR_ACCENT
            )
            entry.pack(side="top", fill="x")
            
            # Sub-label showing group index 1 to 9
            sub_lbl = tk.Label(field_container, text=str(i+1), fg=COLOR_MUTED, bg=COLOR_CARD, font=("Segoe UI", 8))
            sub_lbl.pack(side="top", pady=2)
            
            # Setup keyboard navigation and paste handlers
            entry.bind("<KeyPress>", lambda e, idx=i: self.on_iid_keypress(e, idx))
            entry.bind("<KeyRelease>", lambda e, idx=i: self.on_iid_keyrelease(e, idx))
            entry.bind("<Control-v>", lambda e, idx=i: self.on_iid_paste(e, idx))
            entry.bind("<<Paste>>", lambda e, idx=i: self.on_iid_paste(e, idx))
            
            self.iid_entries.append(entry)
            
        # IID Actions Frame
        iid_actions_frame = tk.Frame(iid_card, bg=COLOR_CARD, pady=5)
        iid_actions_frame.pack(fill="x", pady=(5, 0))
        
        self.btn_capture_iid = self.create_styled_button(
            iid_actions_frame, "Capture Installation ID", self.on_capture_iid_clicked, COLOR_ACCENT
        )
        self.btn_capture_iid.pack(side="left", padx=5)
        
        self.btn_copy_iid = self.create_styled_button(
            iid_actions_frame, "Copy Installation ID", self.on_copy_iid_clicked, COLOR_CARD, has_border=True
        )
        self.btn_copy_iid.pack(side="left", padx=5)
        
        # 3. Card 2: Browser Automation Section
        browser_card = tk.LabelFrame(
            main_container, text=" 2. Browser Activation Portal ",
            fg=COLOR_TEXT, bg=COLOR_CARD, bd=1, relief="solid", font=("Segoe UI", 11, "bold"),
            padx=10, pady=10
        )
        browser_card.pack(fill="x", pady=5)
        
        browser_desc = tk.Label(
            browser_card, text="Open Microsoft activation site, sign in manually, then fill the values:",
            fg=COLOR_MUTED, bg=COLOR_CARD, font=("Segoe UI", 9)
        )
        browser_desc.pack(anchor="w", pady=(0, 10))
        
        browser_actions_frame = tk.Frame(browser_card, bg=COLOR_CARD)
        browser_actions_frame.pack(fill="x")
        
        self.btn_open_web = self.create_styled_button(
            browser_actions_frame, "Open Activation Website", self.on_open_web_clicked, COLOR_ACCENT
        )
        self.btn_open_web.pack(side="left", padx=5)
        
        self.btn_fill_web = self.create_styled_button(
            browser_actions_frame, "Fill Website", self.on_fill_web_clicked, COLOR_CARD, has_border=True
        )
        self.btn_fill_web.pack(side="left", padx=5)
        
        # 4. Card 3: Confirmation ID Section
        cid_card = tk.LabelFrame(
            main_container, text=" 3. Confirmation ID (CID) ",
            fg=COLOR_TEXT, bg=COLOR_CARD, bd=1, relief="solid", font=("Segoe UI", 11, "bold"),
            padx=10, pady=10
        )
        cid_card.pack(fill="x", pady=5)
        
        cid_desc = tk.Label(
            cid_card, text="Retrieve 8 groups of 6 digits (A through H) to complete activation:",
            fg=COLOR_MUTED, bg=COLOR_CARD, font=("Segoe UI", 9)
        )
        cid_desc.pack(anchor="w", pady=(0, 10))
        
        # CID Fields Frame
        cid_fields_frame = tk.Frame(cid_card, bg=COLOR_CARD)
        cid_fields_frame.pack(fill="x", pady=5)
        
        self.cid_entries = []
        labels_ah = ["A", "B", "C", "D", "E", "F", "G", "H"]
        for i in range(8):
            field_container = tk.Frame(cid_fields_frame, bg=COLOR_CARD)
            field_container.pack(side="left", expand=True, padx=2)
            
            entry = tk.Entry(
                field_container, width=7, bg=COLOR_BG, fg=COLOR_TEXT,
                insertbackground=COLOR_TEXT, justify="center", relief="flat",
                font=("Segoe UI", 11, "bold"), highlightbackground=COLOR_BORDER,
                highlightthickness=1, highlightcolor=COLOR_ACCENT
            )
            entry.pack(side="top", fill="x")
            
            sub_lbl = tk.Label(field_container, text=labels_ah[i], fg=COLOR_MUTED, bg=COLOR_CARD, font=("Segoe UI", 8, "bold"))
            sub_lbl.pack(side="top", pady=2)
            
            # Setup keyboard navigation and paste handlers
            entry.bind("<KeyPress>", lambda e, idx=i: self.on_cid_keypress(e, idx))
            entry.bind("<KeyRelease>", lambda e, idx=i: self.on_cid_keyrelease(e, idx))
            entry.bind("<Control-v>", lambda e, idx=i: self.on_cid_paste(e, idx))
            entry.bind("<<Paste>>", lambda e, idx=i: self.on_cid_paste(e, idx))
            
            self.cid_entries.append(entry)
            
        # CID Actions Frame
        cid_actions_frame = tk.Frame(cid_card, bg=COLOR_CARD, pady=5)
        cid_actions_frame.pack(fill="x", pady=(5, 0))
        
        self.btn_capture_cid = self.create_styled_button(
            cid_actions_frame, "Capture / Paste Confirmation ID", self.on_capture_cid_clicked, COLOR_ACCENT
        )
        self.btn_capture_cid.pack(side="left", padx=5)
        
        self.btn_copy_cid = self.create_styled_button(
            cid_actions_frame, "Copy Confirmation ID", self.on_copy_cid_clicked, COLOR_CARD, has_border=True
        )
        self.btn_copy_cid.pack(side="left", padx=5)
        
        self.btn_paste_office = self.create_styled_button(
            cid_actions_frame, "Paste to Office Wizard", self.on_paste_office_clicked, COLOR_CARD, has_border=True
        )
        self.btn_paste_office.pack(side="left", padx=5)
        
        # 5. Log Output Card
        log_card = tk.Frame(main_container, bg=COLOR_BG)
        log_card.pack(fill="both", expand=True, pady=5)
        
        log_lbl = tk.Label(log_card, text="Log Console", fg=COLOR_TEXT, bg=COLOR_BG, font=("Segoe UI", 10, "bold"))
        log_lbl.pack(anchor="w", pady=(0, 2))
        
        self.log_text = scrolledtext.ScrolledText(
            log_card, height=6, bg=COLOR_CARD, fg=COLOR_TEXT, relief="solid", bd=1,
            font=("Consolas", 9), insertbackground=COLOR_TEXT, state="disabled"
        )
        self.log_text.pack(fill="both", expand=True)

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
        Appends a message to the bottom log terminal text widget.
        """
        if not hasattr(self, 'log_text') or not self.log_text.winfo_exists():
            return
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, msg)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

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
                    self.root.after(0, lambda: self.on_ocr_complete(groups))
                else:
                    # Fallback to ScreenSniper
                    self.root.after(0, self.fallback_to_sniper)
            except Exception as e:
                logger.error(f"Auto-detection worker crashed: {e}")
                self.root.after(0, self.fallback_to_sniper)
                
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
                # Run updates on the GUI thread using self.root.after
                self.root.after(0, lambda: self.on_ocr_complete(groups))
            except Exception as e:
                logger.error(f"OCR Worker thread crashed: {e}")
                self.root.after(0, lambda: self.update_status("OCR Failed", "error"))
                
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
        
        def launch_worker():
            success = self.browser_controller.launch()
            if success:
                self.root.after(0, lambda: self.update_status("Browser Active", "success"))
                self.root.after(0, lambda: logger.info("Browser session launched successfully. Please sign in manually."))
                # Start the background pipeline monitor
                monitor_thread = threading.Thread(
                    target=self.browser_controller.start_monitor_pipeline,
                    args=(self.get_iid_list, self.on_cid_scraped_callback),
                    daemon=True
                )
                monitor_thread.start()
            else:
                self.root.after(0, lambda: self.update_status("Launch Failed", "error"))
                self.root.after(0, lambda: messagebox.showerror(
                    "Browser Error",
                    "Failed to launch Chrome or Edge via Selenium.\n"
                    "Verify your browser is installed or try running the tool again."
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
            self.update_status("CID Captured", "success")
            logger.info(f"Automatically scraped Confirmation ID: {''.join(cid_groups)}")
            
            # Focus helper app window
            self.root.deiconify()
            self.root.focus_force()
            self.root.lift()
            
            # Prompt user to paste into Office Wizard
            self.on_paste_office_clicked()
            
        self.root.after(0, gui_update)

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
            success = self.browser_controller.fill_installation_id(groups)
            if success:
                self.root.after(0, lambda: self.update_status("IID Filled", "success"))
            else:
                # Copy to clipboard fallback
                copy_iid_groups(groups)
                self.root.after(0, lambda: self.update_status("Manual Paste Req.", "warning"))
                self.root.after(0, lambda: messagebox.showinfo(
                    "Manual Paste Required",
                    "The automation could not locate the Installation ID input fields on this page.\n\n"
                    "Fallback triggered: The Installation ID has been COPIED to your clipboard.\n"
                    "Please paste it manually into the website fields."
                ))
                
        threading.Thread(target=fill_worker, daemon=True).start()

    def on_capture_cid_clicked(self):
        # 1. First try browser scraping if browser is alive
        if self.browser_controller.is_alive():
            self.update_status("Scraping Browser...", "info")
            logger.info("Attempting to scrape Confirmation ID from browser page...")
            
            # Scrape in thread
            def scrape_worker():
                cid_groups = self.browser_controller.scrape_confirmation_id()
                self.root.after(0, lambda: self.on_scrape_finish(cid_groups))
                
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

        # Always require user confirmation
        confirm = messagebox.askyesno(
            "Auto-Paste Confirmation ID",
            "This action will search for the Microsoft Office Activation Wizard, "
            "bring it to the front, and automatically type the Confirmation ID.\n\n"
            "Would you like to proceed?"
        )
        if not confirm:
            return

        self.update_status("Pasting to Office...", "info")
        
        def paste_worker():
            success = auto_paste_confirmation_id(groups)
            if success:
                self.root.after(0, lambda: self.update_status("Office Activated", "success"))
                self.root.after(0, lambda: logger.info("Successfully pasted Confirmation ID to Office Activation Wizard."))
            else:
                self.root.after(0, lambda: self.update_status("Paste Failed", "warning"))
                self.root.after(0, lambda: self.prompt_manual_paste(groups))
                
        threading.Thread(target=paste_worker, daemon=True).start()

    def prompt_manual_paste(self, groups):
        # Fallback prompts if window bringing/finding failed
        logger.warning("Could not auto-detect Office Activation Wizard window. Triggering fallback countdown.")
        
        # We will create a small countdown window letting the user focus the window manually!
        countdown_win = tk.Toplevel(self.root)
        countdown_win.title("Manual Focus Paste")
        countdown_win.geometry("380x180")
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
                # Run the typing sequence
                paste_cid_to_focused_window(groups)
                self.update_status("Pasted (Focused)", "success")
                
        self.root.after(1000, lambda: tick(4))

    def on_closing(self):
        """
        Called when GUI window is closed. Cleans up browser resources.
        """
        try:
            self.browser_controller.close()
        except Exception:
            pass
        self.root.destroy()
