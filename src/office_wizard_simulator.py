import random
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

class OfficeWizardSimulator(tk.Toplevel):
    """
    A standalone tk.Toplevel window designed to mimic the Microsoft Office Activation Wizard.
    Serves as an authentic training tool for technicians and a test harness for developers.
    """
    def __init__(self, parent):
        super().__init__(parent)
        
        # Set exact window properties to match the real wizard
        self.title("Microsoft Office Activation Wizard")
        
        # Scale window geometry dynamically based on screen DPI
        try:
            self.scale_factor = self.winfo_fpixels('1i') / 96.0
        except Exception:
            self.scale_factor = 1.0
            
        scaled_w = int(620 * self.scale_factor)
        scaled_h = int(560 * self.scale_factor)
        self.geometry(f"{scaled_w}x{scaled_h}")
        self.configure(bg="#ffffff")
        self.resizable(False, False)
        
        # Ensure it stays visible during automation testing
        self.attributes("-topmost", True)
        
        # State variables
        self.iid_groups = ["3000191", "5708926", "9053711", "4144981", "9482725", "1786231", "2355084", "2980272", "5547046"]
        self.cid_entries = []
        
        # Build UI layout
        self.create_widgets()
        
        # Focus country dropdown on startup to match the real wizard
        if hasattr(self, 'country_combo'):
            self.country_combo.focus_set()
            
        # Bind Return key to Next button
        self.bind("<Return>", lambda e: self.on_next())

    def randomize_iid(self):
        """Generates 9 random groups of 7 digits."""
        self.iid_groups = [
            "".join(str(random.randint(0, 9)) for _ in range(7))
            for _ in range(9)
        ]

    def create_widgets(self):
        # --- HEADER SECTION ---
        # Product Title
        product_lbl = tk.Label(
            self, text="Microsoft Office Standard 2016",
            fg="#202020", bg="#ffffff", font=("Segoe UI", 11, "bold")
        )
        product_lbl.place(x=20, y=20)

        # Subtitle
        subtitle_lbl = tk.Label(
            self, text="Activation Wizard",
            fg="#505050", bg="#ffffff", font=("Segoe UI", 9)
        )
        subtitle_lbl.place(x=20, y=42)

        # Office Logo Canvas
        self.logo_canvas = tk.Canvas(self, width=120, height=45, bg="#ffffff", highlightthickness=0)
        self.logo_canvas.place(x=480, y=15)
        
        # Draw the orange Office symbol (a stylized open box / ribbon)
        self.logo_canvas.create_polygon(
            5, 12,   20, 2,   20, 32,   5, 26,
            fill="#d83b01", outline=""
        )
        self.logo_canvas.create_polygon(
            20, 2,   28, 7,   28, 26,   20, 32,
            fill="#eb3c00", outline=""
        )
        self.logo_canvas.create_polygon(
            5, 12,   12, 14,   12, 22,   5, 26,
            fill="#ffffff", outline=""
        )
        
        # Add the text "Office" next to the icon
        self.logo_canvas.create_text(
            35, 17, text="Office", fill="#d83b01",
            font=("Segoe UI", 16, "bold"), anchor="w"
        )

        # --- CONTENT SECTION ---
        # Main instruction
        main_instruct = tk.Label(
            self, text="Follow these steps to activate your software over the telephone.",
            fg="#000000", bg="#ffffff", font=("Segoe UI", 9, "bold")
        )
        main_instruct.place(x=20, y=85)

        # Step 1
        step1_title = tk.Label(
            self, text="Step 1:", fg="#000000", bg="#ffffff", font=("Segoe UI", 9, "bold")
        )
        step1_title.place(x=20, y=115)

        step1_text = tk.Label(
            self, 
            text="Select the country/region you are calling from and call the Product Activation Center using\n"
                 "any of the telephone numbers provided.",
            fg="#000000", bg="#ffffff", font=("Segoe UI", 9), justify="left", anchor="w"
        )
        step1_text.place(x=80, y=115)

        # Styled Combobox
        self.country_combo = ttk.Combobox(
            self, values=["United States", "United Kingdom", "Canada", "Australia", "Germany"],
            font=("Segoe UI", 9)
        )
        self.country_combo.set("select a country/region")
        self.country_combo.place(x=80, y=155, width=320, height=22)

        # Step 2
        step2_title = tk.Label(
            self, text="Step 2:", fg="#000000", bg="#ffffff", font=("Segoe UI", 9, "bold")
        )
        step2_title.place(x=20, y=205)

        step2_text = tk.Label(
            self, text="When prompted, provide this Installation ID:",
            fg="#000000", bg="#ffffff", font=("Segoe UI", 9), justify="left"
        )
        step2_text.place(x=80, y=205)

        # Installation ID Bold text (exactly formatted for easy OCR)
        self.iid_var = tk.StringVar()
        self.update_iid_display()
        
        self.iid_lbl = tk.Label(
            self, textvariable=self.iid_var,
            fg="#000000", bg="#ffffff", font=("Segoe UI", 10, "bold")
        )
        self.iid_lbl.place(x=80, y=230)

        # Step 3
        step3_title = tk.Label(
            self, text="Step 3:", fg="#000000", bg="#ffffff", font=("Segoe UI", 9, "bold")
        )
        step3_title.place(x=20, y=285)

        step3_text = tk.Label(
            self, text="Enter your Confirmation ID here:",
            fg="#000000", bg="#ffffff", font=("Segoe UI", 9), justify="left"
        )
        step3_text.place(x=80, y=285)

        # Confirmation ID Input boxes (A-H)
        labels_ah = ["A", "B", "C", "D", "E", "F", "G", "H"]
        start_x = 80
        box_width = 46
        gap = 12
        
        self.cid_entries = []
        for i in range(8):
            x_pos = start_x + i * (box_width + gap)
            
            # Label A-H centered above the box
            lbl = tk.Label(
                self, text=labels_ah[i], fg="#505050", bg="#ffffff", 
                font=("Segoe UI", 8, "bold"), width=5
            )
            lbl.place(x=x_pos, y=312)
            
            entry = tk.Entry(
                self, width=6, bg="#ffffff", fg="#000000",
                justify="center", relief="solid", bd=1,
                font=("Segoe UI", 10)
            )
            entry.place(x=x_pos, y=332, width=box_width, height=24)
            
            # Key bindings for tabbing and pasting
            entry.bind("<KeyPress>", lambda e, idx=i: self.on_cid_keypress(e, idx))
            entry.bind("<KeyRelease>", lambda e, idx=i: self.on_cid_keyrelease(e, idx))
            entry.bind("<Control-v>", lambda e, idx=i: self.on_cid_paste(e, idx))
            entry.bind("<<Paste>>", lambda e, idx=i: self.on_cid_paste(e, idx))
            
            self.cid_entries.append(entry)

        # Temporary developer/technician utility buttons (for training setup)
        util_frame = tk.Frame(self, bg="#ffffff")
        util_frame.place(x=80, y=380)

        btn_random = tk.Button(
            util_frame, text="Randomize IID", command=self.on_randomize_clicked,
            bg="#f3f3f3", fg="#333333", relief="solid", bd=1, padx=8, font=("Segoe UI", 8)
        )
        btn_random.pack(side="left")

        btn_clear = tk.Button(
            util_frame, text="Clear Fields", command=self.on_clear_clicked,
            bg="#f3f3f3", fg="#333333", relief="solid", bd=1, padx=8, font=("Segoe UI", 8)
        )
        btn_clear.pack(side="left", padx=10)

        # Privacy link
        privacy_lbl = tk.Label(
            self, text="Privacy Statement", fg="#0f7fd5", bg="#ffffff",
            font=("Segoe UI", 9, "underline"), cursor="hand2"
        )
        privacy_lbl.place(x=510, y=472)
        privacy_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://go.microsoft.com/fwlink/?LinkId=521839"))

        # --- FOOTER BUTTONS BAR ---
        # Line separator
        sep = tk.Frame(self, height=1, bg="#d0d0d0")
        sep.place(x=0, y=500, width=620)

        footer_bar = tk.Frame(self, bg="#f0f0f0", height=60)
        footer_bar.place(x=0, y=501, width=620)

        # Helper to style Windows-like footer buttons
        def create_footer_button(parent, text, command, x, is_default=False):
            # Focus border color
            border_color = "#0f7fd5" if is_default else "#a0a0a0"
            btn = tk.Button(
                parent, text=text, command=command, bg="#ffffff", fg="#000000",
                relief="solid", bd=1, font=("Segoe UI", 9), highlightcolor=border_color,
                activebackground="#f4f4f4"
            )
            btn.place(x=x, y=16, width=90, height=26)
            return btn

        create_footer_button(footer_bar, "Help", self.on_help, 20)
        create_footer_button(footer_bar, "Back", lambda: None, 310)
        self.btn_next = create_footer_button(footer_bar, "Next", self.on_next, 410, is_default=True)
        create_footer_button(footer_bar, "Cancel", self.destroy, 510)

    def update_iid_display(self):
        """Formats the generated Installation ID for realistic layout display."""
        text = " ".join(self.iid_groups)
        self.iid_var.set(text)

    def on_randomize_clicked(self):
        self.randomize_iid()
        self.update_iid_display()
        self.on_clear_clicked()

    def on_clear_clicked(self):
        for entry in self.cid_entries:
            entry.delete(0, tk.END)
        if self.cid_entries:
            self.cid_entries[0].focus_set()

    def on_help(self):
        messagebox.showinfo(
            "Activation Help",
            "This is a simulator window representing the Microsoft Office Activation Wizard.\n\n"
            "Use it to train technicians on configuring telephone activations or verifying OCR capture."
        )

    def on_next(self, event=None):
        full_cid = "".join(e.get().strip() for e in self.cid_entries)
        if len(full_cid) == 48:
            self.show_success_screen()
        else:
            messagebox.showwarning(
                "Microsoft Office Activation",
                "The Confirmation ID entered is incomplete. It must consist of 8 groups of 6 digits (48 digits total)."
            )

    def show_success_screen(self):
        """
        Mimics the final success screen of the real Office Activation Wizard.
        """
        # Create a frame that covers the upper content area
        success_frame = tk.Frame(self, bg="#ffffff")
        success_frame.place(x=0, y=80, width=620, height=420)
        
        # Success title
        success_title = tk.Label(
            success_frame, text="Thank you. Your copy of Microsoft Office has been activated.",
            fg="#000000", bg="#ffffff", font=("Segoe UI", 10, "bold"), anchor="w", justify="left"
        )
        success_title.pack(anchor="w", padx=20, pady=20)
        
        # Success description
        success_desc = tk.Label(
            success_frame, 
            text="Products activated successfully.\n"
                 "You have activated Office.\n\n"
                 "Please click Close to exit the Activation Wizard.",
            fg="#202020", bg="#ffffff", font=("Segoe UI", 9), anchor="w", justify="left"
        )
        success_desc.pack(anchor="w", padx=20, pady=10)
        
        # Change the Next button in the footer to "Close"
        self.btn_next.config(text="Close", command=self.destroy)
        
        # Rebind Return key to Close (destroy)
        self.bind("<Return>", lambda e: self.destroy())

    # --- Auto-tabbing and tabbing handling ---

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
        # Ignore control/navigation keys
        if event.keysym in ["Tab", "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Left", "Right", "Up", "Down", "BackSpace"]:
            return
            
        val = self.cid_entries[index].get()
        # Keep only digits
        digits = "".join(c for c in val if c.isdigit())
        
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
            text = self.clipboard_get()
        except Exception:
            return "break"
            
        digits = "".join(c for c in text if c.isdigit())
        if not digits:
            return "break"
            
        if len(digits) >= 48:
            # Full CID paste: distribute starting from box A
            for i in range(8):
                self.cid_entries[i].delete(0, tk.END)
                self.cid_entries[i].insert(0, digits[i*6:(i+1)*6])
            self.cid_entries[7].focus_set()
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
            
        return "break"
