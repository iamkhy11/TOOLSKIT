import ctypes
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import webbrowser
import platform
import psutil
import uuid
import getpass
import os
import subprocess
import socket
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import dns.resolver
import urllib.request
import urllib.error
import json
import urllib.parse

class NSCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JOKESKY-V3.0.2 Scanner - Pro Edition (High Performance)")
        self.root.geometry("780x640")
        self.root.minsize(740, 600)
        
        self.set_dark_title_bar()
        
        # Status Mode (Dark / Light)
        self.is_dark_mode = True
        self.apply_theme_colors()
        
        self.bulk_domains = []
        self.remaining_domains = [] # Menyimpan sisa domain saat di-pause
        self.scan_results_cache = []
        self.is_running = False
        self.is_paused = False # Flag status Pause
        self.start_time = 0
        self.ui_queue = queue.Queue()
        self.get_counter = 0  # Counter melacak jumlah domain GET
        
        # Inisialisasi info System
        self.user_info = self.get_exact_username()
        self.device_info = self.get_exact_device_model()
        self.geo_info = "Mendeteksi..."
        self.ip_info = "Memuat IP..."
        self.mac_info = self.get_mac_address()
        self.fps_info = "60 FPS (Stable)"
        
        threading.Thread(target=self.fetch_geo_ip, daemon=True).start()
        
        self.root.configure(bg=self.bg_color)
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        self.update_ttk_styles()

        # === 1. BOX UTAMA (NOTEBOOK TAB) ===
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(10, 4))
        
        # Tab 1: Live Scan
        tab_scan = ttk.Frame(self.notebook)
        self.notebook.add(tab_scan, text="  Live Scan  ")
        
        self.live_status_var = tk.StringVar(value="Creat Worker . . .")
        self.live_status_lbl = tk.Label(
            tab_scan, textvariable=self.live_status_var, bg=self.card_bg, fg="#fbbf24", 
            font=("Consolas", 10, "bold"), anchor=tk.W, padx=10, pady=6, relief=tk.FLAT
        )
        self.live_status_lbl.pack(side=tk.TOP, fill=tk.X, padx=2, pady=(2, 4))
        
        self.root.after(800, lambda: [self.live_status_var.set("Upload Worker . . ."), self.live_status_lbl.config(fg="#fbbf24")])
        self.root.after(1600, lambda: [self.live_status_var.set("System Ready . . ."), self.live_status_lbl.config(fg="#34d399")])

        self.prompt_text = tk.Text(
            tab_scan, bg=self.card_bg, fg=self.text_white, font=("Consolas", 9),
            relief=tk.FLAT, bd=0, highlightthickness=0, state=tk.DISABLED, wrap=tk.NONE
        )
        v_scroll1 = ttk.Scrollbar(tab_scan, orient=tk.VERTICAL, command=self.prompt_text.yview)
        self.prompt_text.configure(yscrollcommand=v_scroll1.set)
        
        self.prompt_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2), pady=4)
        v_scroll1.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        # Tab 2: System & Hardware Info
        tab_sys = ttk.Frame(self.notebook)
        self.notebook.add(tab_sys, text="  System & Hardware  ")
        
        self.sys_text = tk.Text(
            tab_sys, bg=self.card_bg, fg=self.accent_cyan, font=("Consolas", 10),
            relief=tk.FLAT, bd=0, highlightthickness=0, state=tk.DISABLED, wrap=tk.NONE
        )
        self.sys_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        
        self.init_hardware_info()
        self.update_live_clock()

        # === 2. PROGRESS BAR ===
        prog_frame = tk.Frame(root, bg=self.bg_color, padx=12, pady=2)
        prog_frame.pack(fill=tk.X)
        
        self.progress_bar = ttk.Progressbar(prog_frame, orient=tk.HORIZONTAL, mode='determinate', style="Clean.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, expand=True)

        # === 3. ETA & COUNTER ===
        eta_counter_frame = tk.Frame(root, bg=self.bg_color, padx=12, pady=2)
        eta_counter_frame.pack(fill=tk.X)
        
        self.eta_var = tk.StringVar(value="ETA: 00:00:00")
        self.eta_lbl = tk.Label(eta_counter_frame, textvariable=self.eta_var, bg=self.bg_color, fg="#fbbf24", font=("Segoe UI", 9, "bold"))
        self.eta_lbl.pack(side=tk.LEFT)
        
        self.counter_var = tk.StringVar(value="")
        self.counter_lbl = tk.Label(eta_counter_frame, textvariable=self.counter_var, bg=self.bg_color, fg="#34d399", font=("Segoe UI", 9, "bold"))
        self.counter_lbl.pack(side=tk.RIGHT)

        # === 4. PANEL KONTROL UTAMA ===
        main_control_frame = tk.Frame(root, bg=self.bg_color, padx=12, pady=8)
        main_control_frame.pack(fill=tk.X)
        
        btn_w = 13
        dropdown_w = 14
        
        # --- BOX KIRI ---
        left_box = tk.Frame(main_control_frame, bg=self.bg_color)
        left_box.pack(side=tk.LEFT, anchor=tk.NW)
        
        target_row = tk.Frame(left_box, bg=self.bg_color)
        target_row.pack(anchor=tk.W, pady=(0, 4))
        
        self.lbl_target = tk.Label(target_row, text="Target:", bg=self.bg_color, fg=self.text_dim, font=("Segoe UI", 9, "bold"))
        self.lbl_target.pack(side=tk.LEFT, padx=(0, 6))
        
        self.placeholder_text = "Masukan Domain"
        self.domain_entry = tk.Entry(
            target_row, bg=self.card_bg, fg=self.text_dim, font=("Segoe UI", 9), width=22,
            relief=tk.FLAT, insertbackground=self.accent_cyan, highlightthickness=1,
            highlightbackground="#3f3f46", highlightcolor=self.accent_cyan
        )
        self.domain_entry.pack(side=tk.LEFT, ipady=5, padx=(0, 6))
        self.domain_entry.insert(0, self.placeholder_text)
        
        self.domain_entry.bind("<FocusIn>", self.on_entry_focus_in)
        self.domain_entry.bind("<FocusOut>", self.on_entry_focus_out)

        self.get_counter_var = tk.StringVar(value="GET: 0")
        self.get_counter_lbl = tk.Label(
            target_row, textvariable=self.get_counter_var, bg=self.card_bg, fg="#34d399",
            font=("Consolas", 9, "bold"), padx=8, pady=4, relief=tk.FLAT
        )
        self.get_counter_lbl.pack(side=tk.LEFT, ipady=2)
        
        dropdown_row = tk.Frame(left_box, bg=self.bg_color)
        dropdown_row.pack(anchor=tk.W, pady=(2, 0))
        
        self.mode_var = tk.StringVar(value="NONE")
        self.mode_cb = ttk.Combobox(dropdown_row, textvariable=self.mode_var, values=["NONE", "NS", "A Rec", "HTTP", "301/302"], width=dropdown_w, state="readonly")
        self.mode_cb.pack(side=tk.LEFT, padx=(0, 6))
        
        ns_platforms = [
            "NONE", "Semua NS", "Cloudflare", "DigitalOcean", "AWS (Route 53)", 
            "CloudFront", "Fastly", "BunnyCDN", "Hostinger", "Google Cloud", 
            "Vercel", "Netlify", "GoDaddy", "Namecheap", "Bluehost", 
            "HostGator", "Linode", "Vultr", "SiteGround", "DreamHost", "NameSilo", "Porkbun"
        ]
        self.filter_var = tk.StringVar(value="NONE")
        self.filter_cb = ttk.Combobox(dropdown_row, textvariable=self.filter_var, values=ns_platforms, width=dropdown_w, state="readonly")
        self.filter_cb.pack(side=tk.LEFT, padx=(0, 6))

        self.worker_var = tk.StringVar(value="NONE")
        self.worker_cb = ttk.Combobox(dropdown_row, textvariable=self.worker_var, values=["NONE", "Speed 10", "Speed 20", "Speed 50", "Speed 80", "Speed 100"], width=dropdown_w, state="readonly")
        self.worker_cb.pack(side=tk.LEFT, padx=0)

        # --- BOX KANAN ---
        right_box = tk.Frame(main_control_frame, bg=self.bg_color)
        right_box.pack(side=tk.RIGHT, anchor=tk.NE)
        
        top_buttons_frame = tk.Frame(right_box, bg=self.bg_color)
        top_buttons_frame.pack(anchor=tk.E, pady=(0, 4))
        
        col_left = tk.Frame(top_buttons_frame, bg=self.bg_color)
        col_left.pack(side=tk.LEFT, padx=(0, 6))
        
        col_right = tk.Frame(top_buttons_frame, bg=self.bg_color)
        col_right.pack(side=tk.LEFT, padx=0)
        
        self.import_btn = tk.Button(
            col_left, text="Import", bg=self.btn_bg, fg=self.text_white, font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT, activebackground="#3f3f46", activeforeground=self.text_white, cursor="hand2",
            command=self.import_domains_file, width=btn_w
        )
        self.import_btn.pack(anchor=tk.E, pady=(0, 4), ipady=4)
        
        self.terminal_btn = tk.Button(
            col_left, text="Terminal", bg=self.btn_bg, fg=self.text_white, font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT, activebackground="#3f3f46", activeforeground=self.text_white, cursor="hand2",
            command=self.open_terminal_window, width=btn_w
        )
        self.terminal_btn.pack(anchor=tk.E, pady=0, ipady=4)
        
        self.export_btn = tk.Button(
            col_right, text="Export Menu", bg=self.btn_bg, fg=self.text_white, font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT, activebackground="#3f3f46", activeforeground=self.text_white, cursor="hand2",
            command=self.open_export_menu, width=btn_w
        )
        self.export_btn.pack(anchor=tk.E, pady=(0, 4), ipady=4)
        
        self.theme_switch_btn = tk.Button(
            col_right, text="DARK" if self.is_dark_mode else "LIGHT", bg=self.btn_bg, fg=self.text_white, font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT, activebackground="#3f3f46", activeforeground=self.text_white, width=btn_w, command=self.toggle_theme, cursor="hand2"
        )
        self.theme_switch_btn.pack(anchor=tk.E, pady=0, ipady=4)

        action_row = tk.Frame(right_box, bg=self.bg_color)
        action_row.pack(anchor=tk.E, pady=(4, 0))
        
        self.clear_btn = tk.Button(
            action_row, text="Clear", bg="#52525b", fg=self.text_white, font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT, activebackground="#71717a", cursor="hand2", command=self.clear_app, width=btn_w
        )
        self.clear_btn.pack(side=tk.RIGHT, padx=(6, 0), ipady=4)
        
        self.stop_btn = tk.Button(
            action_row, text="Pause", bg="#f59e0b", fg=self.text_white, font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT, activebackground="#fbbf24", cursor="hand2", command=self.toggle_pause, state=tk.DISABLED, width=btn_w
        )
        self.stop_btn.pack(side=tk.RIGHT, padx=6, ipady=4)
        
        self.search_btn = tk.Button(
            action_row, text="Scan", bg=self.accent_cyan, fg="#000000" if self.is_dark_mode else "#ffffff", font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT, activebackground="#22d3ee", cursor="hand2", command=self.start_process, width=btn_w
        )
        self.search_btn.pack(side=tk.RIGHT, padx=0, ipady=4)

        bottom_status_frame = tk.Frame(root, bg=self.bg_color, padx=12, pady=6)
        bottom_status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_var = tk.StringVar(value="Sistem Siap. Silakan pilih konfigurasi terlebih dahulu.")
        self.status_lbl = tk.Label(bottom_status_frame, textvariable=self.status_var, bg=self.bg_color, fg=self.accent_cyan, font=("Segoe UI", 9))
        self.status_lbl.pack(side=tk.LEFT)

        self.prompt_text.tag_configure("success", foreground="#34d399")
        self.prompt_text.tag_configure("error", foreground="#ef4444")
        self.prompt_text.tag_configure("info", foreground="#22d3ee")
        self.prompt_text.tag_configure("dim", foreground="#71717a")

        self.root.after(50, self.process_ui_queue)

    def save_session_cache(self):
        try:
            if self.scan_results_cache:
                with open("scan_cache.json", "w", encoding="utf-8") as f:
                    json.dump(self.scan_results_cache, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def open_terminal_window(self):
        term_win = tk.Toplevel(self.root)
        term_win.title("JOKESKY-V3.0.2 - Integrated Terminal")
        term_win.geometry("750x480")
        term_win.configure(bg=self.bg_color)
        term_win.transient(self.root)

        lbl_info = tk.Label(
            term_win, text=f"Terminal Emulator ({platform.system()} - {self.user_info})", 
            bg=self.card_bg, fg=self.accent_cyan, font=("Consolas", 9, "bold"), anchor=tk.W, padx=10, pady=6
        )
        lbl_info.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(8, 4))

        text_frame = tk.Frame(term_win, bg=self.bg_color)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        term_text = tk.Text(
            text_frame, bg=self.card_bg, fg="#34d399" if self.is_dark_mode else "#0f172a", 
            font=("Consolas", 9), relief=tk.FLAT, bd=0, highlightthickness=0, wrap=tk.WORD
        )
        term_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=term_text.yview)
        term_text.configure(yscrollcommand=term_scroll.set)

        term_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        term_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        term_text.insert(tk.END, f"JOKESKY-V3.0.2 Pro Terminal Initialized.\nKetik perintah sistem Anda di bawah ini...\n\n")
        term_text.config(state=tk.DISABLED)

        input_frame = tk.Frame(term_win, bg=self.bg_color, padx=8, pady=8)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)

        prompt_lbl = tk.Label(input_frame, text=">", bg=self.bg_color, fg=self.accent_cyan, font=("Consolas", 10, "bold"))
        prompt_lbl.pack(side=tk.LEFT, padx=(0, 4))

        cmd_entry = tk.Entry(
            input_frame, bg=self.card_bg, fg=self.text_white, font=("Consolas", 10),
            relief=tk.FLAT, insertbackground=self.accent_cyan, highlightthickness=1,
            highlightbackground="#3f3f46", highlightcolor=self.accent_cyan
        )
        cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        cmd_entry.focus_set()

        def execute_cmd(event=None):
            command = cmd_entry.get().strip()
            if not command:
                return
            cmd_entry.delete(0, tk.END)
            term_text.config(state=tk.NORMAL)
            term_text.insert(tk.END, f"> {command}\n", "cmd")
            term_text.config(state=tk.DISABLED)
            term_text.see(tk.END)

            if command.lower() == "clear":
                term_text.config(state=tk.NORMAL)
                term_text.delete("1.0", tk.END)
                term_text.config(state=tk.DISABLED)
                return

            def run_process():
                try:
                    process = subprocess.Popen(
                        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore'
                    )
                    stdout, stderr = process.communicate()
                    output = stdout + stderr
                    if not output.strip():
                        output = "[Perintah selesai tanpa output]\n"

                    def update_term_output():
                        term_text.config(state=tk.NORMAL)
                        term_text.insert(tk.END, output + "\n")
                        term_text.config(state=tk.DISABLED)
                        term_text.see(tk.END)

                    self.ui_queue.put(update_term_output)
                except Exception as e:
                    err_msg = f"Error: {str(e)}\n"
                    self.ui_queue.put(lambda: [
                        term_text.config(state=tk.NORMAL),
                        term_text.insert(tk.END, err_msg),
                        term_text.config(state=tk.DISABLED),
                        term_text.see(tk.END)
                    ])

            threading.Thread(target=run_process, daemon=True).start()

        cmd_entry.bind("<Return>", execute_cmd)

    def get_exact_username(self):
        try:
            return os.environ.get('USERNAME') or os.environ.get('USER') or getpass.getuser()
        except Exception:
            return "User"

    def get_exact_device_model(self):
        try:
            if platform.system() == "Windows":
                m_output = subprocess.check_output("wmic computersystem get manufacturer", shell=True).decode(errors="ignore").split('\n')
                mo_output = subprocess.check_output("wmic computersystem get model", shell=True).decode(errors="ignore").split('\n')
                manufacturer = [line.strip() for line in m_output if line.strip() and line.strip() != "Manufacturer"]
                model = [line.strip() for line in mo_output if line.strip() and line.strip() != "Model"]
                m_str = manufacturer[0] if manufacturer else ""
                mo_str = model[0] if model else ""
                if m_str or mo_str:
                    return f"{m_str} {mo_str}".strip()
            return platform.node() or "PC System"
        except Exception:
            return platform.node() or "Standard Device"

    def get_mac_address(self):
        try:
            mac_num = uuid.getnode()
            mac_addr = ':'.join(['{:02x}'.format((mac_num >> elements) & 0xff) for elements in range(40,-1,-8)])
            return mac_addr.upper()
        except Exception:
            return "00:00:00:00:00:00"

    def fetch_geo_ip(self):
        try:
            req = urllib.request.urlopen("https://ipapi.co/json/", timeout=4)
            data = json.loads(req.read().decode('utf-8'))
            self.ip_info = data.get('ip', 'Unknown')
            country = data.get('country_name', 'Unknown')
            city = data.get('city', '')
            self.geo_info = f"{country} ({city})" if city else country
        except Exception:
            try:
                req = urllib.request.urlopen("https://api64.ipify.org?format=json", timeout=4)
                data = json.loads(req.read().decode('utf-8'))
                self.ip_info = data.get('ip', 'Unknown')
                self.geo_info = "Indonesia (Detected)"
            except Exception:
                self.ip_info = "127.0.0.1 (Offline)"
                self.geo_info = "Local Device"

    def check_internet_connection(self):
        """Metode Cepat & Akurat via Socket TCP (Anti Blocking ISP)"""
        for host, port in [("1.1.1.1", 53), ("8.8.8.8", 53)]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.5)
                sock.connect((host, port))
                sock.close()
                return True
            except Exception:
                continue
        return False

    def on_entry_focus_in(self, event):
        if self.domain_entry.get() == self.placeholder_text:
            self.domain_entry.delete(0, tk.END)
            self.domain_entry.config(fg=self.text_white)

    def on_entry_focus_out(self, event):
        if not self.domain_entry.get().strip():
            self.domain_entry.insert(0, self.placeholder_text)
            self.domain_entry.config(fg=self.text_dim)

    def apply_theme_colors(self):
        if self.is_dark_mode:
            self.bg_color = "#121214"
            self.card_bg = "#1a1a1e"
            self.accent_cyan = "#06b6d4"
            self.text_white = "#f4f4f5"
            self.text_dim = "#a1a1aa"
            self.btn_bg = "#27272a"
        else:
            self.bg_color = "#f1f5f9"
            self.card_bg = "#ffffff"
            self.accent_cyan = "#0284c7"
            self.text_white = "#0f172a"
            self.text_dim = "#64748b"
            self.btn_bg = "#e2e8f0"

    def update_ttk_styles(self):
        self.style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#ffffff", foreground="#000000", padding=[10, 5], font=("Segoe UI", 8, "bold"))
        self.style.map("TNotebook.Tab", 
                       background=[('selected', self.accent_cyan), ('!selected', '#ffffff')], 
                       foreground=[('selected', '#000000' if self.is_dark_mode else '#ffffff'), ('!selected', '#000000')],
                       padding=[('selected', [16, 10]), ('!selected', [10, 5])],
                       font=[('selected', ('Segoe UI', 10, 'bold')), ('!selected', ('Segoe UI', 8, 'bold'))])
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("Clean.Horizontal.TProgressbar", troughcolor="#27272a" if self.is_dark_mode else "#e2e8f0", background=self.accent_cyan, borderwidth=0, thickness=6)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme_colors()
        self.update_ttk_styles()
        
        self.root.configure(bg=self.bg_color)
        for widget in self.root.winfo_children():
            self._update_widget_colors(widget)
            
        self.theme_switch_btn.config(text="DARK" if self.is_dark_mode else "LIGHT", bg=self.btn_bg, fg=self.text_white)
        self.search_btn.config(fg="#000000" if self.is_dark_mode else "#ffffff")
        
        if hasattr(self, 'live_status_lbl'):
            self.live_status_lbl.config(bg=self.card_bg)
        if hasattr(self, 'get_counter_lbl'):
            self.get_counter_lbl.config(bg=self.card_bg)
        
        if self.domain_entry.get() == self.placeholder_text:
            self.domain_entry.config(fg=self.text_dim)

    def _update_widget_colors(self, widget):
        w_type = widget.winfo_class()
        if w_type in ['Frame', 'TFrame']:
            widget.configure(bg=self.bg_color)
            for child in widget.winfo_children():
                self._update_widget_colors(child)
        elif w_type == 'Label':
            widget.configure(bg=self.bg_color)
            if widget != self.eta_lbl and widget != self.counter_lbl and widget != self.status_lbl and widget != getattr(self, 'live_status_lbl', None) and widget != getattr(self, 'get_counter_lbl', None):
                widget.configure(fg=self.text_dim)
        elif w_type == 'Text':
            widget.configure(bg=self.card_bg, fg=self.text_white)
        elif w_type == 'Entry':
            widget.configure(bg=self.card_bg)
            if widget.get() != self.placeholder_text:
                widget.configure(fg=self.text_white)

    def set_dark_title_bar(self):
        try:
            self.root.update()
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int(1)))
        except Exception:
            pass

    def init_hardware_info(self):
        try:
            self.os_info = f"{platform.system()} {platform.release()}"
            self.cpu_info = platform.processor() or "AMD / Intel x64 Architecture"
            self.ram_info = f"{round(psutil.virtual_memory().total / (1024.0 ** 3), 1)} GB"
        except Exception:
            self.os_info = "Windows 11"
            self.cpu_info = "Detected Device CPU"
            self.ram_info = "16.0 GB"

    def update_live_clock(self):
        try:
            now_time = datetime.now().strftime("%H:%M:%S WIB")
            now_date = datetime.now().strftime("%d-%m-%Y")
            
            hw_content = (
                f"  APPLICATION INFO\n"
                f"  --------------------------------------------------\n"
                f"  VERSION  : JKSY-V.3.0.2 Pro (High Speed Edition)\n"
                f"  TIME     : {now_time} | DATE: {now_date}\n"
                f"  OS       : {self.os_info}\n"
                f"  USER     : {self.user_info}\n"
                f"  DEVICE   : {self.device_info}\n"
                f"  CPU      : {self.cpu_info}\n"
                f"  RAM      : {self.ram_info}\n"
                f"  GEO      : {self.geo_info}\n"
                f"  IP       : {self.ip_info}\n"
                f"  MAC'A    : {self.mac_info}\n"
                f"  FPS      : {self.fps_info}\n"
                f"  CREATOR  : JOKESKYLS\n"
                f"  TELEGRAM : @nazisme1930\n"
                f"  STATUS   : High-Performance Engine Active"
            )
            
            self.sys_text.config(state=tk.NORMAL)
            self.sys_text.delete("1.0", tk.END)
            self.sys_text.insert(tk.END, hw_content)
            self.sys_text.config(state=tk.DISABLED)
        except Exception:
            pass
        
        self.root.after(1000, self.update_live_clock)

    def import_domains_file(self):
        file_path = filedialog.askopenfilename(
            title="Pilih File Daftar Domain (.txt)",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    self.bulk_domains = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
                    self.remaining_domains = list(self.bulk_domains)
                
                filename_only = file_path.split("/")[-1].split("\\")[-1]
                self.domain_entry.delete(0, tk.END)
                self.domain_entry.config(fg=self.text_white)
                self.domain_entry.insert(0, filename_only)
                self.status_var.set(f"Berhasil memuat file: {filename_only} ({len(self.bulk_domains)} domain)")
                self.counter_var.set(f"0 / {len(self.bulk_domains)}")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal membaca file: {str(e)}")

    def open_export_menu(self):
        if not self.scan_results_cache:
            messagebox.showwarning("Peringatan", "Belum ada hasil scan yang dapat diproses!")
            return

        export_win = tk.Toplevel(self.root)
        export_win.title("Export Manager")
        export_win.geometry("340x240")
        export_win.configure(bg=self.bg_color)
        export_win.resizable(False, False)
        export_win.transient(self.root)
        export_win.grab_set()

        lbl_title = tk.Label(export_win, text="Export Files", bg=self.bg_color, fg=self.accent_cyan, font=("Segoe UI", 10, "bold"))
        lbl_title.pack(pady=(15, 10))

        btn_save = tk.Button(
            export_win, text="Save Files", bg="#0284c7", fg="#ffffff", font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT, command=lambda: [self.export_save_all(), export_win.destroy()]
        )
        btn_save.pack(fill=tk.X, padx=20, pady=5, ipady=6)

        btn_loss = tk.Button(
            export_win, text="Save Broken", bg="#ef4444", fg="#ffffff", font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT, command=lambda: [self.export_take_loss(), export_win.destroy()]
        )
        btn_loss.pack(fill=tk.X, padx=20, pady=5, ipady=6)

        btn_donate = tk.Button(
            export_win, text="Developer", bg="#10b981", fg="#ffffff", font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT, command=lambda: [webbrowser.open("https://t.me/nazisme1930"), export_win.destroy()]
        )
        btn_donate.pack(fill=tk.X, padx=20, pady=5, ipady=6)

    def export_save_all(self):
        current_mode = self.mode_var.get()
        if current_mode == "NONE" or not self.scan_results_cache:
            messagebox.showwarning("Peringatan", "Pilih fungsi yang valid atau lakukan scan terlebih dahulu!")
            return

        if current_mode == "NS":
            selected_filter = self.filter_var.get()
            if selected_filter == "NONE":
                messagebox.showwarning("Peringatan", "Silakan pilih filter platform NS terlebih dahulu untuk melakukan export!")
                return
            
            filtered = []
            for item in self.scan_results_cache:
                if item.get('mode') == 'NS' and item.get('result'):
                    ns_records = item['result']
                    if selected_filter == "Semua NS":
                        filtered.append(item['domain'])
                    else:
                        match = any(selected_filter.lower() in ns.lower() for ns in ns_records)
                        if match:
                            filtered.append(item['domain'])
        elif current_mode in ["HTTP", "301/302"]:
            filtered = [item['domain'] for item in self.scan_results_cache if item.get('mode') == current_mode and item.get('result')]
        else:
            filtered = [item['domain'] for item in self.scan_results_cache if item.get('mode') == 'A Rec' and item.get('result')]

        if not filtered:
            messagebox.showinfo("Info", f"Tidak ada domain sukses yang cocok untuk filter '{self.filter_var.get()}' ini.")
            return
            
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(filtered))
            messagebox.showinfo("Sukses", f"Berhasil menyimpan {len(filtered)} domain terfilter.")

    def export_take_loss(self):
        loss = [item['domain'] for item in self.scan_results_cache if not item['result']]
        if not loss:
            messagebox.showinfo("Info", "Tidak ada domain gagal.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(loss))
            messagebox.showinfo("Sukses", f"Berhasil menyimpan {len(loss)} domain Take Loss.")

    def start_process(self):
        current_mode = self.mode_var.get()
        current_speed = self.worker_var.get()
        
        if current_mode == "NONE":
            self.live_status_var.set("No Function Selected . . .")
            self.live_status_lbl.config(fg="#ef4444")
            messagebox.showwarning("Peringatan", "Silakan pilih fungsi pada dropdown terlebih dahulu!")
            return

        if current_speed == "NONE":
            self.live_status_var.set("No Speed Selected . . .")
            self.live_status_lbl.config(fg="#ef4444")
            messagebox.showwarning("Peringatan", "Silakan pilih Speed / Worker terlebih dahulu!")
            return

        if not self.check_internet_connection():
            self.live_status_var.set("System Scan Lost Connection . . .")
            self.live_status_lbl.config(fg="#ef4444")
            messagebox.showerror("Koneksi Terputus", "Tidak ada koneksi internet!")
            return

        if not self.remaining_domains or not self.is_paused:
            if self.bulk_domains:
                self.remaining_domains = list(self.bulk_domains)
            else:
                val = self.domain_entry.get().strip()
                if val and val != self.placeholder_text:
                    self.remaining_domains = [val]
                    self.bulk_domains = [val]
                else:
                    messagebox.showwarning("Peringatan", "Masukkan domain atau import file terlebih dahulu!")
                    return
            self.scan_results_cache = []
            self.get_counter = 0
            self.get_counter_var.set("GET: 0")
            self.prompt_text.config(state=tk.NORMAL)
            self.prompt_text.delete("1.0", tk.END)
            self.prompt_text.config(state=tk.DISABLED)

        try:
            max_workers = int(''.join(filter(str.isdigit, current_speed)))
        except Exception:
            max_workers = 20

        self.is_running = True
        self.is_paused = False
        self.start_time = time.time()
        
        self.live_status_var.set("System Scan Running . . .")
        self.live_status_lbl.config(fg="#38bdf8")

        self.search_btn.config(state=tk.DISABLED)
        self.import_btn.config(state=tk.DISABLED)
        self.stop_btn.config(text="Pause", bg="#f59e0b", state=tk.NORMAL)
        
        total = len(self.bulk_domains)
        done_count = total - len(self.remaining_domains)
        self.counter_var.set(f"{done_count} / {total}")
        self.progress_bar['maximum'] = total
        self.progress_bar['value'] = done_count
        self.eta_var.set("ETA: 00:00:00")
        
        threading.Thread(target=self.run_scanner_thread, args=(list(self.remaining_domains), max_workers, total, done_count), daemon=True).start()

    def toggle_pause(self):
        if self.is_running and not self.is_paused:
            self.is_running = False
            self.is_paused = True
            self.stop_btn.config(text="Resume", bg="#3b82f6")
            self.live_status_var.set("System Scan Pause . . .")
            self.live_status_lbl.config(fg="#ef4444")
            self.status_var.set("Proses dipause. Tekan 'Resume' untuk melanjutkan.")
        elif self.is_paused:
            self.start_process()

    def clear_app(self):
        self.is_running = False
        self.is_paused = False
        self.scan_results_cache = []
        self.bulk_domains = []
        self.remaining_domains = []
        self.get_counter = 0
        self.get_counter_var.set("GET: 0")
        self.prompt_text.config(state=tk.NORMAL)
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.config(state=tk.DISABLED)
        self.domain_entry.delete(0, tk.END)
        self.domain_entry.insert(0, self.placeholder_text)
        self.domain_entry.config(fg=self.text_dim)
        self.progress_bar['value'] = 0
        self.counter_var.set("")
        self.eta_var.set("ETA: 00:00:00")
        self.status_var.set("Sistem Siap.")
        
        self.live_status_var.set("System Ready . . .")
        self.live_status_lbl.config(fg="#34d399")
        self.reset_buttons()

    def reset_buttons(self):
        self.is_running = False
        self.is_paused = False
        self.search_btn.config(state=tk.NORMAL)
        self.import_btn.config(state=tk.NORMAL)
        self.stop_btn.config(text="Pause", bg="#f59e0b", state=tk.DISABLED)

    def log_to_prompt(self, text, tag=""):
        self.prompt_text.config(state=tk.NORMAL)
        self.prompt_text.insert(tk.END, text + "\n", tag)
        self.prompt_text.see(tk.END)
        self.prompt_text.config(state=tk.DISABLED)

    def process_ui_queue(self):
        try:
            count = 0
            while not self.ui_queue.empty() and count < 150:
                task = self.ui_queue.get_nowait()
                task()
                count += 1
        except Exception:
            pass
        try:
            if self.root.winfo_exists():
                self.root.after(30, self.process_ui_queue)
        except Exception:
            pass

    def clean_ns_name(self, ns):
        ns_lower = ns.lower()
        if 'cloudflare' in ns_lower: return 'Cloudflare'
        elif 'digitalocean' in ns_lower: return 'DigitalOcean'
        elif 'awsdns' in ns_lower or 'amazon' in ns_lower or 'route53' in ns_lower: return 'AWS (Route 53)'
        elif 'cloudfront' in ns_lower: return 'CloudFront'
        elif 'fastly' in ns_lower: return 'Fastly'
        elif 'bunny' in ns_lower: return 'BunnyCDN'
        elif 'hostinger' in ns_lower: return 'Hostinger'
        elif 'google' in ns_lower: return 'Google Cloud'
        elif 'vercel' in ns_lower: return 'Vercel'
        elif 'netlify' in ns_lower: return 'Netlify'
        elif 'domaincontrol' in ns_lower: return 'GoDaddy'
        elif 'namecheap' in ns_lower: return 'Namecheap'
        else:
            parts = ns.rstrip('.').split('.')
            if len(parts) >= 2:
                return f"{parts[-2]}.{parts[-1]}"
            return ns

    def run_scanner_thread(self, current_batch, max_workers, total, initial_done):
        completed = initial_done
        
        # Resolver Terakselerasi
        fast_resolver = dns.resolver.Resolver(configure=False)
        fast_resolver.nameservers = ['1.1.1.1', '1.0.0.1', '8.8.8.8']
        fast_resolver.timeout = 1.0
        fast_resolver.lifetime = 1.0

        def scan_one(domain):
            if not self.is_running:
                return None

            clean_dom = domain.replace("https://", "").replace("http://", "").strip("/")
            current_mode = self.mode_var.get()

            if current_mode == "NS":
                ns_list = []
                try:
                    answers = fast_resolver.resolve(clean_dom, 'NS')
                    for r in answers:
                        ns_list.append(str(r).rstrip('.').lower())
                except Exception:
                    pass
                return (domain, clean_dom, "NS", ns_list)

            elif current_mode == "A Rec":
                a_list = []
                try:
                    answers = fast_resolver.resolve(clean_dom, 'A')
                    for r in answers:
                        a_list.append(str(r))
                except Exception:
                    pass

                if not a_list:
                    try:
                        ip_addr = socket.gethostbyname(clean_dom)
                        if ip_addr:
                            a_list.append(ip_addr)
                    except Exception:
                        pass

                return (domain, clean_dom, "A Rec", list(set(a_list)))

            elif current_mode == "HTTP":
                status_result = None
                try:
                    req = urllib.request.Request(f"http://{clean_dom}", headers={'User-Agent': 'Mozilla/5.0'})
                    res = urllib.request.urlopen(req, timeout=2.0)
                    status_result = f"{res.getcode()} OK"
                except urllib.error.HTTPError as e:
                    status_result = f"{e.code} Error"
                except Exception:
                    pass
                
                return (domain, clean_dom, "HTTP", [status_result] if status_result else [])

            elif current_mode == "301/302":
                redirect_info = None
                try:
                    class RedirectTracker(urllib.request.HTTPRedirectHandler):
                        def __init__(self):
                            self.redirect_url = None
                            self.code = None

                        def redirect_request(self, req, fp, code, msg, headers, newurl):
                            self.code = code
                            self.redirect_url = newurl
                            return None

                    tracker = RedirectTracker()
                    opener = urllib.request.build_opener(tracker)
                    req = urllib.request.Request(f"http://{clean_dom}", headers={'User-Agent': 'Mozilla/5.0'})
                    
                    try:
                        opener.open(req, timeout=2.0)
                        redirect_info = "200 OK (Clear)"
                    except urllib.error.HTTPError as e:
                        if e.code in [301, 302, 303, 307, 308]:
                            target_url = tracker.redirect_url
                            if target_url:
                                parsed_target = urllib.parse.urlparse(target_url)
                                target_domain = parsed_target.netloc.lower().replace("www.", "")
                                base_clean = clean_dom.lower().replace("www.", "")
                                
                                if target_domain and target_domain != base_clean:
                                    redirect_info = f"{e.code} -> {target_domain}"
                                else:
                                    redirect_info = f"{e.code} Clear"
                            else:
                                redirect_info = f"{e.code} Clear"
                        else:
                            redirect_info = f"{e.code} Error"
                except Exception:
                    pass
                
                return (domain, clean_dom, "301/302", [redirect_info] if redirect_info else [])

            return (domain, clean_dom, "NONE", [])

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(scan_one, d): d for d in current_batch}
            for fut in as_completed(futures):
                if not self.is_running:
                    break
                res = fut.result()
                if not res:
                    continue
                orig_dom, dom, mode_type, res_arr = res
                completed += 1
                
                if orig_dom in self.remaining_domains:
                    self.remaining_domains.remove(orig_dom)
                
                self.scan_results_cache.append({'domain': dom, 'mode': mode_type, 'result': res_arr})
                
                is_match_get = False
                selected_filter = self.filter_var.get()
                if mode_type == "NS" and res_arr:
                    if selected_filter == "Semua NS":
                        is_match_get = True
                    elif selected_filter != "NONE":
                        is_match_get = any(selected_filter.lower() in ns.lower() for ns in res_arr)
                elif mode_type in ["A Rec", "HTTP", "301/302"] and res_arr:
                    is_match_get = True

                if is_match_get:
                    self.get_counter += 1

                elapsed = time.time() - self.start_time
                scanned_in_this_run = completed - initial_done
                if scanned_in_this_run > 0:
                    avg = elapsed / scanned_in_this_run
                    eta_sec = int(avg * (total - completed))
                    hours, rem = divmod(eta_sec, 3600)
                    mins, secs = divmod(rem, 60)
                    eta_str = f"ETA: {hours:02d}:{mins:02d}:{secs:02d}"
                else:
                    eta_str = "ETA: 00:00:00"

                def update_ui(c, d_name, m_type, r_arr, e_s, match_flag):
                    if not self.is_running:
                        return
                    self.counter_var.set(f"{c} / {total}")
                    self.progress_bar['value'] = c
                    self.eta_var.set(e_s)
                    
                    if match_flag:
                        self.get_counter_var.set(f"GET: {self.get_counter}")
                    
                    self.log_to_prompt(f"[{c}/{total}] {d_name}", "info")
                    
                    if m_type == "NS":
                        if r_arr:
                            primary = next((x for x in r_arr if 'ns1' in x), r_arr[0])
                            cleaned_name = self.clean_ns_name(primary)
                            padded_name = cleaned_name.ljust(22)
                            get_indicator = "(GET)" if len(r_arr) > 1 else ""
                            disp = f"{padded_name} {get_indicator}".strip()
                            self.log_to_prompt(f"   └─ NS: {disp}", "success")
                        else:
                            self.log_to_prompt(f"   └─ NS: Tidak Tersedia", "error")
                    elif m_type == "A Rec":
                        if r_arr:
                            ip_str = ", ".join(r_arr)
                            self.log_to_prompt(f"   └─ IP: {ip_str}", "success")
                        else:
                            self.log_to_prompt(f"   └─ IP: Tidak Tersedia", "error")
                    elif m_type == "HTTP":
                        if r_arr:
                            self.log_to_prompt(f"   └─ HTTP: {r_arr[0]}", "success" if "OK" in r_arr[0] else "error")
                        else:
                            self.log_to_prompt(f"   └─ HTTP: Offline / Timeout", "error")
                    elif m_type == "301/302":
                        if r_arr:
                            is_external_redirect = "->" in r_arr[0]
                            self.log_to_prompt(f"   └─ REDIRECT: {r_arr[0]}", "success" if is_external_redirect else "info")
                        else:
                            self.log_to_prompt(f"   └─ REDIRECT: Offline / Timeout", "error")

                self.ui_queue.put(lambda cc=completed, dn=dom, mt=mode_type, ra=res_arr, es=eta_str, mf=is_match_get: update_ui(cc, dn, mt, ra, es, mf))

        if self.is_running and not self.remaining_domains:
            self.save_session_cache()
            self.ui_queue.put(lambda: [
                self.live_status_var.set("System Scan Done . . ."),
                self.live_status_lbl.config(fg="#34d399"),
                self.status_var.set("Pemindaian selesai! Hasil otomatis disimpan ke cache.")
            ])
            self.ui_queue.put(lambda: self.eta_var.set("ETA: 00:00:00"))
            self.ui_queue.put(self.reset_buttons)

if __name__ == "__main__":
    # Hanya proses yang diluncurkan oleh aplikasi.py yang diizinkan
    # membuka GUI Scanner. Pengecekan ini bukan proteksi anti-modifikasi kode.
    import sys

    authorized = (
        os.environ.pop("JKSY_SCANNER_LAUNCH", None) == "launcher-v1"
        and os.environ.pop("JKSY_SCANNER_PARENT_PID", None) == str(os.getppid())
    )
    if not authorized:
        print("ACCESS DENIED: Scanner hanya dapat dibuka melalui aplikasi.py.")
        sys.exit(1)

    root = tk.Tk()
    app = NSCheckerApp(root)
    root.mainloop()