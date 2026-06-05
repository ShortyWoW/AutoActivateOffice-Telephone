import random
import tkinter as tk
from tkinter import ttk

class OfficeWizardSimulator(tk.Toplevel):
    """
    A standalone tk.Toplevel window designed to mimic the Microsoft Office Activation Wizard.
    Serves as a training tool for new technicians and a test harness for the developer.
    """
    def __init__(self, parent):
        super().__init__(parent)
        
        # Win32 target window title (used for window detection by office_window.py)
        self.title("Microsoft Office Activation Wizard (Training Simulator)")
        self.geometry("680x480")
        self.configure(bg="#f3f3f3")
        self.resizable(False, False)
        
        # Ensure it stays on top of the main app for easy visibility
        self.attributes("-topmost", True)
        
        # State variables
        self.iid_groups = []
        self.cid_entries = []
        
        # Generate initial Installation ID
        self.randomize_iid()
        
        # Build UI layout
        self.create_widgets()
        
        # Auto-focus first entry
        if self.cid_entries:
            self.cid_entries[0].focus_set()

    def randomize_iid(self):
        """Generates 9 random groups of 7 digits."""
        self.iid_groups = [
            "".join(str(random.randint(0, 9)) for _ in range(7))
            for _ in range(9)
        ]

    def create_widgets(self):
        # 1. Header Banner
        header_frame = tk.Frame(self, bg="#0078d4", height=70) # Classic Microsoft Blue
        header_frame.pack(fill="x", side="top")
        header_frame.pack_propagate(False)
        
        header_lbl = tk.Label(
            header_frame, 
            text="Microsoft Office Activation Wizard (Training Mode)", 
            fg="white", bg="#0078d4", 
            font=("Segoe UI", 12, "bold"),
            padx=15, pady=20
        )
        header_lbl.pack(side="left")

        # Main content area
        content_frame = tk.Frame(self, bg="#f3f3f3", padx=20, pady=15)
        content_frame.pack(fill="both", expand=True)

        # 2. Training instructions
        instruct_lbl = tk.Label(
            content_frame,
            text="Step 1: Use the Helper Tool to capture the Installation ID below (OCR or Auto-detect).\n"
                 "Step 2: Auto-fill the portal to obtain your 48-digit Confirmation ID.\n"
                 "Step 3: Click 'Paste to Office Wizard' in the Helper Tool to auto-type it here.",
            fg="#404040", bg="#f3f3f3", justify="left", font=("Segoe UI", 9, "italic")
        )
        instruct_lbl.pack(anchor="w", pady=(0, 15))

        # 3. Installation ID (IID) Frame
        iid_frame = tk.LabelFrame(
            content_frame, text=" Installation ID (IID) ",
            fg="#0078d4", bg="white", font=("Segoe UI", 10, "bold"), bd=1, relief="solid",
            padx=15, pady=15
        )
        iid_frame.pack(fill="x", pady=10)

        # Installation ID display
        self.iid_lbl_var = tk.StringVar()
        self.update_iid_display()
        
        iid_display = tk.Label(
            iid_frame, textvariable=self.iid_lbl_var,
            fg="#202020", bg="white", font=("Consolas", 12, "bold"),
            padx=5, pady=5, relief="flat"
        )
        iid_display.pack(fill="x")

        # 4. Confirmation ID (CID) Frame
        cid_frame = tk.LabelFrame(
            content_frame, text=" Confirmation ID (CID) ",
            fg="#0078d4", bg="white", font=("Segoe UI", 10, "bold"), bd=1, relief="solid",
            padx=15, pady=15
        )
        cid_frame.pack(fill="x", pady=10)

        cid_desc = tk.Label(
            cid_frame, text="Enter the confirmation ID in the boxes below:",
            fg="#404040", bg="white", font=("Segoe UI", 9)
        )
        cid_desc.pack(anchor="w", pady=(0, 5))

        # Entry Grid (A to H)
        entries_frame = tk.Frame(cid_frame, bg="white")
        entries_frame.pack(fill="x", pady=5)

        self.cid_entries = []
        labels_ah = ["A", "B", "C", "D", "E", "F", "G", "H"]
        for i in range(8):
            field_container = tk.Frame(entries_frame, bg="white")
            field_container.pack(side="left", expand=True, padx=4)
            
            entry = tk.Entry(
                field_container, width=6, bg="#ffffff", fg="#202020",
                justify="center", relief="solid", bd=1,
                font=("Consolas", 11, "bold")
            )
            entry.pack(side="top", fill="x")
            
            sub_lbl = tk.Label(
                field_container, text=labels_ah[i], 
                fg="#606060", bg="white", font=("Segoe UI", 8, "bold")
            )
            sub_lbl.pack(side="top", pady=2)
            
            # Bind keystrokes for auto-tabbing and validation
            entry.bind("<KeyPress>", lambda e, idx=i: self.on_cid_keypress(e, idx))
            entry.bind("<KeyRelease>", lambda e, idx=i: self.on_cid_keyrelease(e, idx))
            
            self.cid_entries.append(entry)

        # 5. Controls Frame
        controls_frame = tk.Frame(content_frame, bg="#f3f3f3")
        controls_frame.pack(fill="x", pady=(15, 0))

        btn_random = tk.Button(
            controls_frame, text="Randomize Installation ID", 
            command=self.on_randomize_clicked, bg="#e1e1e1", fg="#202020",
            relief="groove", padx=10, pady=4, font=("Segoe UI", 9)
        )
        btn_random.pack(side="left")

        btn_reset = tk.Button(
            controls_frame, text="Reset Fields", 
            command=self.on_reset_clicked, bg="#e1e1e1", fg="#202020",
            relief="groove", padx=10, pady=4, font=("Segoe UI", 9)
        )
        btn_reset.pack(side="left", padx=10)

        # 6. Status Indicator
        self.status_lbl = tk.Label(
            controls_frame, text="Status: Waiting for Activation Key...",
            fg="#606060", bg="#e1e1e1", font=("Segoe UI", 9, "bold"),
            padx=12, pady=5, relief="flat"
        )
        self.status_lbl.pack(side="right")

    def update_iid_display(self):
        """Formats the generated Installation ID for clear layout display."""
        # Split into blocks of 3 for the window screenshot rendering
        text = "   ".join(self.iid_groups)
        self.iid_lbl_var.set(text)

    def on_randomize_clicked(self):
        self.randomize_iid()
        self.update_iid_display()
        self.on_reset_clicked()

    def on_reset_clicked(self):
        for entry in self.cid_entries:
            entry.delete(0, tk.END)
        self.status_lbl.config(
            text="Status: Waiting for Activation Key...", 
            bg="#e1e1e1", fg="#606060"
        )
        if self.cid_entries:
            self.cid_entries[0].focus_set()

    # --- Auto-tabbing and simulation detection ---

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
            self.check_activation_status()
            return
            
        val = self.cid_entries[index].get()
        # Ensure only numeric digits
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
                
        self.check_activation_status()

    def check_activation_status(self):
        """Scans CID entry fields and lights up green if all 48 digits are populated."""
        full_cid = "".join(e.get().strip() for e in self.cid_entries)
        if len(full_cid) == 48:
            self.status_lbl.config(
                text="Status: Activated (Simulation Mode)!", 
                bg="#2ea043", fg="white" # Success Green
            )
        else:
            self.status_lbl.config(
                text="Status: Typing/Pasting...", 
                bg="#d29922", fg="white" # Warning Amber
            )
