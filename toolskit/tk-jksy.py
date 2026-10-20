import asyncio
import aiohttp
import hashlib
import base64
import threading
import os
import platform
import datetime
import subprocess
import shutil
import time
import customtkinter as ctk
from tkinter import filedialog

try:
    import psutil
except ImportError:
    psutil = None

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

internal_stk = "04789992e0eed99a36184d3b3a59b82f"
_encoded_url = "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL2lhbWtoeTExL2QtamtzeS9yZWZzL2hlYWRzL21haW4vZGdvLWRvbWFpbnMudHh0"
GITHUB_RAW_URL = base64.b64decode(_encoded_url).decode('utf-8')
_enc_priv_key = "am9rZXNreTE5MzA="

BTN_WIDTH = 80
BTN_HEIGHT = 28

TLD_LIST = [
    ".Private",
    ".com", ".net", ".org", ".info", ".biz", ".name", ".pro", ".xyz", ".online", ".site", 
    ".tech", ".store", ".shop", ".app", ".dev", ".io", ".co", ".me", ".cc", ".tv", ".ws", 
    ".icu", ".top", ".vip", ".club", ".fun", ".space", ".press", ".news", ".media", ".studio", 
    ".agency", ".expert", ".solutions", ".services", ".systems", ".network", ".global", ".cloud", 
    ".digital", ".finance", ".ventures", ".holdings", ".partners", ".company", ".limited", ".today", 
    ".live", ".life", ".world", ".email", ".link", ".click", ".support", ".center",
    ".id", ".co.id", ".or.id", ".sch.id", ".ac.id", ".net.id", ".go.id", ".mil.id", ".my.id", ".web.id", ".biz.id", ".desa.id",
    ".asia", ".sg", ".my", ".ph", ".th", ".vn", ".in", ".jp", ".kr", ".cn", ".hk", ".tw", 
    ".au", ".nz", ".bn", ".kh", ".la", ".mm", ".pk", ".bd", ".lk", ".np", ".mv", ".mn",
    ".eu", ".uk", ".co.uk", ".org.uk", ".de", ".fr", ".it", ".es", ".nl", ".ru", ".ch", ".se", 
    ".no", ".fi", ".dk", ".pl", ".pt", ".gr", ".ie", ".at", ".be", ".cz", ".hu", ".ro", ".ua", 
    ".us", ".ca", ".mx", ".br", ".ar", ".cl", ".co", ".pe", ".ve", ".ec", ".bo", ".py", ".uy", 
    ".ae", ".sa", ".qa", ".kw", ".bh", ".om", ".jo", ".lb", ".il", ".tr", ".eg", ".za", ".ng"
]

class JKSYApp(ctk.CTk):
    def __init__(self, launcher_ref=None):
        super().__init__()

        self.launcher_ref = launcher_ref  # Referensi ke aplikasi.py untuk fungsi logout

        self.title("Jokekyls Takeover update v.2.1.2 - Private")
        self.geometry("800x700")
        self.resizable(False, False)

        self.is_scanning = False
        self.stop_requested = False
        self.scanned_count = 0
        self.imported_domains = []
        
        self.is_private_active = False
        self.is_point_private = False
        self.current_speed = 10
        self.is_master_unlocked = False

        self.build_main_menu()

        # Tombol X pada title bar kembali ke dashboard launcher, sama seperti Logout.
        self.protocol("WM_DELETE_WINDOW", self.logout_to_login)

    def logout_to_login(self):
        if self.is_scanning:
            self.stop_scanning()
        self.destroy()
        if self.launcher_ref:
            self.launcher_ref.deiconify() # Memunculkan kembali jendela launcher aplikasi.py

    def toggle_theme_switch(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

    def show_auth_locked_warning(self):
        warn_dialog = ctk.CTkToplevel(self)
        warn_dialog.title("Access Locked")
        warn_dialog.geometry("360x180")
        warn_dialog.resizable(False, False)
        warn_dialog.attributes("-topmost", True)

        lbl_title = ctk.CTkLabel(warn_dialog, text="🔒 Authen Key Is Lock", font=("Segoe UI", 15, "bold"), text_color="#FF5555")
        lbl_title.pack(pady=(22, 6))

        lbl_sub = ctk.CTkLabel(warn_dialog, text="Membutuhkan Akses Auth Key Master", font=("Segoe UI", 12), text_color="gray")
        lbl_sub.pack(pady=(0, 15))

        btn_ok = ctk.CTkButton(
            warn_dialog, text="OK / Verify Key", command=lambda: [warn_dialog.destroy(), self.show_master_key_popup()], 
            width=130, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#1f538d", hover_color="#143c68"
        )
        btn_ok.pack()

    def show_master_key_popup(self):
        if self.is_master_unlocked:
            self.is_master_unlocked = False
            self.btn_key.configure(text="🔒 Key", fg_color="#c92a2a", hover_color="#a61e1e")
            self.log_boxes("Auth Key Master Terkunci Kembali.", "KEY LOCKED", "yellow")
            return

        auth_dialog = ctk.CTkToplevel(self)
        auth_dialog.title("Master Auth Verification")
        auth_dialog.geometry("380x200")
        auth_dialog.resizable(False, False)
        auth_dialog.attributes("-topmost", True)

        lbl_title = ctk.CTkLabel(auth_dialog, text="🔑 Masukkan Master Auth Key", font=("Segoe UI", 13, "bold"))
        lbl_title.pack(pady=(20, 10))

        key_entry = ctk.CTkEntry(auth_dialog, placeholder_text="Enter Auth Key ...", show="*", width=300, height=35, font=("Segoe UI", 12))
        key_entry.pack(pady=5)
        key_entry.focus()

        err_label = ctk.CTkLabel(auth_dialog, text="", text_color="#FF5555", font=("Segoe UI", 11))
        err_label.pack(pady=2)

        def verify_master_key():
            entered_key = key_entry.get().strip()
            decoded_key = base64.b64decode(_enc_priv_key).decode('utf-8')
            if hashlib.md5(entered_key.encode()).hexdigest() == hashlib.md5(decoded_key.encode()).hexdigest():
                self.is_master_unlocked = True
                self.btn_key.configure(text="🔓 Key", fg_color="#2b8a3e", hover_color="#216e31")
                self.log_boxes("Master Auth Key Berhasil Terverifikasi! Semua fitur spesial siap digunakan.", "SUCCESS", "green")
                auth_dialog.destroy()
            else:
                err_label.configure(text="❌ Auth Key Salah!")

        key_entry.bind("<Return>", lambda event: verify_master_key())

        btn_submit = ctk.CTkButton(auth_dialog, text="Verify Key", command=verify_master_key, width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#2b8a3e", hover_color="#216e31")
        btn_submit.pack(pady=10)

    def build_main_menu(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=2)

        title_label = ctk.CTkLabel(header_frame, text="⚡ JOKESKY DOMAIN TAKEOVER", font=("Segoe UI", 16, "bold"))
        title_label.pack(side="left")

        version_badge = ctk.CTkLabel(header_frame, text=" JKSY-V.2.1.2 ", font=("Segoe UI", 11, "bold"), fg_color="#1f538d", text_color="white", corner_radius=6)
        version_badge.pack(side="left", padx=10)

        content_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=10)
        content_frame.pack(fill="both", expand=True, padx=12, pady=(0, 5))

        boxes_container = ctk.CTkFrame(content_frame, fg_color="transparent")
        boxes_container.pack(fill="both", expand=True, padx=10, pady=(2, 1))

        lbl_left = ctk.CTkLabel(boxes_container, text="📂 Domain Target (Live Scan)", font=("Consolas", 11, "bold"), text_color=("#333333", "gray"), anchor="w")
        lbl_left.grid(row=0, column=0, sticky="w", padx=(0, 5), pady=(0, 1))

        lbl_right = ctk.CTkLabel(boxes_container, text="📊 Status Hasil", font=("Consolas", 11, "bold"), text_color=("#333333", "gray"), anchor="w")
        lbl_right.grid(row=0, column=1, sticky="w", padx=(5, 0), pady=(0, 1))

        self.box_domain = ctk.CTkTextbox(boxes_container, width=500, height=270, font=("Consolas", 12), fg_color=("#f0f0f0", "#000000"), text_color=("#008000", "#00FF66"))
        self.box_domain.grid(row=1, column=0, padx=(0, 5))
        self.box_domain.configure(state="disabled")

        self.box_status = ctk.CTkTextbox(boxes_container, width=260, height=270, font=("Consolas", 12), fg_color=("#f0f0f0", "#000000"), text_color=("#000000", "#FFFFFF"))
        self.box_status.grid(row=1, column=1, padx=(5, 0))
        
        self.box_status._textbox.tag_config("green", foreground="#00aa00" if ctk.get_appearance_mode()=="Light" else "#00FF66")
        self.box_status._textbox.tag_config("red", foreground="#cc0000" if ctk.get_appearance_mode()=="Light" else "#FF4444")
        self.box_status._textbox.tag_config("yellow", foreground="#b58900" if ctk.get_appearance_mode()=="Light" else "#FFD700")
        self.box_status._textbox.tag_config("normal", foreground="#333333" if ctk.get_appearance_mode()=="Light" else "#AAAAAA")
        self.box_status.configure(state="disabled")

        progress_container = ctk.CTkFrame(boxes_container, fg_color="transparent")
        progress_container.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 1))

        self.progress_bar = ctk.CTkProgressBar(progress_container, orientation="horizontal", height=10, progress_color="#2b8a3e")
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.progress_bar.set(0.0)

        self.progress_label = ctk.CTkLabel(progress_container, text="0%", font=("Consolas", 11, "bold"), text_color=("#2b8a3e", "#00FF66"), width=45)
        self.progress_label.pack(side="right")

        timer_container = ctk.CTkFrame(boxes_container, fg_color=("#e9ecef", "#1a1a1a"), corner_radius=6)
        timer_container.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 4))

        self.timer_label = ctk.CTkLabel(timer_container, text="⭐ Status Akses : Aktif & Terverifikasi", font=("Consolas", 11, "bold"), text_color=("#2b8a3e", "#00FF66"))
        self.timer_label.pack(side="left", padx=10, pady=4)

        btn_pro = ctk.CTkButton(
            timer_container, text="💬 Admin", command=lambda: webbrowser.open("https://t.me/nazisme1930"), width=BTN_WIDTH, height=24, 
            font=("Segoe UI", 11, "bold"), fg_color="#1f538d", text_color="white", hover_color="#143c68"
        )
        btn_pro.pack(side="right", padx=8, pady=4)

        extra_boxes_container = ctk.CTkFrame(content_frame, fg_color="transparent")
        extra_boxes_container.pack(fill="both", expand=True, padx=10, pady=(1, 1))

        lbl_info = ctk.CTkLabel(extra_boxes_container, text="⚙️ System & Hardware", font=("Consolas", 11, "bold"), text_color=("#333333", "gray"), anchor="w")
        lbl_info.grid(row=0, column=0, sticky="w", padx=(0, 5), pady=(0, 1))

        self.box_info = ctk.CTkTextbox(extra_boxes_container, width=380, height=115, font=("Consolas", 10), fg_color=("#f0f0f0", "#000000"), text_color=("#0055aa", "#00FFFF"))
        self.box_info.grid(row=1, column=0, padx=(0, 10))
        self.box_info.configure(state="disabled")

        right_panel_frame = ctk.CTkFrame(extra_boxes_container, fg_color=("#e9ecef", "#1a1a1a"), width=370, height=115, corner_radius=8)
        right_panel_frame.grid(row=1, column=1, sticky="nsew")
        right_panel_frame.pack_propagate(False)

        self.theme_switch = ctk.CTkSwitch(
            right_panel_frame, text="Light/Night", command=self.toggle_theme_switch,
            font=("Segoe UI", 11, "bold"), progress_color="#2b8a3e"
        )
        self.theme_switch.pack(anchor="w", padx=15, pady=(8, 6))
        
        if ctk.get_appearance_mode() == "Dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()

        tools_btn_container = ctk.CTkFrame(right_panel_frame, fg_color="transparent")
        tools_btn_container.pack(anchor="w", padx=15, pady=(0, 5))

        key_color = "#2b8a3e" if self.is_master_unlocked else "#c92a2a"
        key_hover = "#216e31" if self.is_master_unlocked else "#a61e1e"
        key_text = "🔓 Key" if self.is_master_unlocked else "🔒 Key"

        self.btn_key = ctk.CTkButton(
            tools_btn_container, text=key_text, command=self.show_master_key_popup, width=BTN_WIDTH, height=BTN_HEIGHT, 
            font=("Segoe UI", 11, "bold"), fg_color=key_color, text_color="white", hover_color=key_hover
        )
        self.btn_key.pack(side="left", padx=(0, 6))

        btn_netstat = ctk.CTkButton(
            tools_btn_container, text="Terminal", command=self.show_netstat_popup, width=BTN_WIDTH, height=BTN_HEIGHT, 
            font=("Segoe UI", 11, "bold"), fg_color="#1f538d", text_color="white", hover_color="#143c68"
        )
        btn_netstat.pack(side="left")

        btn_ns_check = ctk.CTkButton(
            right_panel_frame, text="Checker", command=self.show_ns_checker_popup, width=BTN_WIDTH, height=BTN_HEIGHT, 
            font=("Segoe UI", 11, "bold"), fg_color="#2b8a3e", text_color="white", hover_color="#216e31"
        )
        btn_ns_check.pack(anchor="w", padx=15, pady=(0, 6))

        filter_action_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        filter_action_frame.pack(fill="x", padx=10, pady=2)

        input_container = ctk.CTkFrame(filter_action_frame, fg_color="transparent")
        input_container.pack(side="left", fill="x", expand=True, padx=(0, 8))

        filter_label = ctk.CTkLabel(input_container, text="🎯 Filter Output TLD :", font=("Segoe UI", 11, "bold"), text_color=("#333333", "gray"))
        filter_label.pack(anchor="w", pady=(0, 1))

        entry_btn_box = ctk.CTkFrame(input_container, fg_color="transparent")
        entry_btn_box.pack(fill="x", expand=True)

        self.filter_entry = ctk.CTkEntry(entry_btn_box, placeholder_text="Command ...", height=BTN_HEIGHT, font=("Segoe UI", 12))
        self.filter_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.filter_entry.configure(state="disabled")

        self.btn_point = ctk.CTkButton(
            entry_btn_box, text="Point", command=self.show_tld_picker_popup, width=BTN_WIDTH, height=BTN_HEIGHT, 
            font=("Segoe UI", 11, "bold"), fg_color="#d35400", hover_color="#b54600", text_color="white"
        )
        self.btn_point.pack(side="left", padx=(0, 4))

        self.btn_speed = ctk.CTkButton(
            entry_btn_box, text=f"⚡ {self.current_speed}", command=self.show_speed_picker_popup, width=BTN_WIDTH, height=BTN_HEIGHT, 
            font=("Segoe UI", 11, "bold"), fg_color="#2b8a3e", hover_color="#216e31", text_color="white"
        )
        self.btn_speed.pack(side="right")

        button_container = ctk.CTkFrame(filter_action_frame, fg_color="transparent")
        button_container.pack(side="right", anchor="s")

        self.btn_scan = ctk.CTkButton(
            button_container, text="🔒 Scan", command=self.start_scanning_thread, 
            width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), 
            fg_color="#555555", text_color="white", state="disabled"
        )
        self.btn_scan.pack(side="left", padx=(0, 4))

        self.btn_stop = ctk.CTkButton(
            button_container, text="🛑 Stop", command=self.stop_scanning, 
            width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), 
            fg_color="#c92a2a", text_color="white", hover_color="#a61e1e", state="disabled"
        )
        self.btn_stop.pack(side="left")

        bottom_action_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        bottom_action_frame.pack(fill="x", padx=10, pady=(1, 3))

        left_bottom_btns = ctk.CTkFrame(bottom_action_frame, fg_color="transparent")
        left_bottom_btns.pack(side="left")

        btn_result = ctk.CTkButton(
            left_bottom_btns, text="📁 Box", command=self.show_results_popup, 
            width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), text_color="white"
        )
        btn_result.pack(side="left", padx=(0, 4))

        btn_import = ctk.CTkButton(
            left_bottom_btns, text="📥 Import", command=self.import_external_file, 
            width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), 
            fg_color="#1f538d", text_color="white", hover_color="#143c68"
        )
        btn_import.pack(side="left", padx=(0, 4))

        priv_color = "#1f538d" if self.is_private_active else "#c92a2a"
        priv_hover = "#143c68" if self.is_private_active else "#a61e1e"
        priv_text = "🔒 Private" if self.is_private_active else "🔐 Private"
        
        self.btn_private = ctk.CTkButton(
            left_bottom_btns, text=priv_text, command=self.handle_private_button, 
            width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), 
            fg_color=priv_color, text_color="white", hover_color=priv_hover
        )
        self.btn_private.pack(side="left", padx=(0, 4))

        btn_clear = ctk.CTkButton(
            left_bottom_btns, text="🗑️ Clear", command=self.clear_files, 
            width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), 
            fg_color="#495057", text_color="white", hover_color="#343a40"
        )
        btn_clear.pack(side="left")

        right_bottom_container = ctk.CTkFrame(bottom_action_frame, fg_color="transparent")
        right_bottom_container.pack(side="right")

        # Tombol Logout untuk kembali ke aplikasi.py
        btn_logout = ctk.CTkButton(
            right_bottom_container, text="🚪 Logout", command=self.logout_to_login, 
            width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), 
            fg_color="#343a40", text_color="white", hover_color="#212529"
        )
        btn_logout.pack(side="left", padx=(0, 8))

        counter_frame = ctk.CTkFrame(right_bottom_container, fg_color=("#e9ecef", "#1a1a1a"), corner_radius=8, height=BTN_HEIGHT)
        counter_frame.pack(side="left")

        self.counter_label = ctk.CTkLabel(counter_frame, text="🔔 Total Domain: 0", font=("Segoe UI", 11, "bold"), text_color=("#2b8a3e", "#00FF66"))
        self.counter_label.pack(padx=12, pady=4)

        self.log_boxes("System initialized (update v.2.1.2)...\n", "System Ready", "normal")
        threading.Thread(target=self.update_realtime_clock, daemon=True).start()

    def show_speed_picker_popup(self):
        speed_dialog = ctk.CTkToplevel(self)
        speed_dialog.title("Setting Speed Scan")
        speed_dialog.geometry("480x320")
        speed_dialog.resizable(False, False)
        speed_dialog.attributes("-topmost", True)

        lbl_title = ctk.CTkLabel(speed_dialog, text="⚡ Pilih Kecepatan Scan", font=("Segoe UI", 15, "bold"))
        lbl_title.pack(pady=(15, 2))

        lbl_sub = ctk.CTkLabel(speed_dialog, text="Atur speed sesuai stabilitas jaringan untuk mencegah crash.", font=("Segoe UI", 11), text_color="gray")
        lbl_sub.pack(pady=(0, 15))

        main_columns_frame = ctk.CTkFrame(speed_dialog, fg_color="transparent")
        main_columns_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        left_col = ctk.CTkFrame(main_columns_frame, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        lbl_free = ctk.CTkLabel(left_col, text="⚪ Free Speed:", font=("Segoe UI", 12, "bold"), text_color="#AAAAAA")
        lbl_free.pack(anchor="w", pady=(0, 8))

        btn_s10 = ctk.CTkButton(
            left_col, text="Speed 10", command=lambda: self.set_speed_value(10, speed_dialog),
            width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#1f538d", hover_color="#143c68"
        )
        btn_s10.pack(pady=(0, 8), fill="x")

        btn_s20 = ctk.CTkButton(
            left_col, text="Speed 20", command=lambda: self.set_speed_value(20, speed_dialog),
            width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#1f538d", hover_color="#143c68"
        )
        btn_s20.pack(pady=(0, 8), fill="x")

        right_col = ctk.CTkFrame(main_columns_frame, fg_color="transparent")
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))

        lbl_pro = ctk.CTkLabel(right_col, text="🔒 Pro / Ultra Speed:", font=("Segoe UI", 12, "bold"), text_color="#FFD700")
        lbl_pro.pack(anchor="w", pady=(0, 8))

        def trigger_pro_speed(target_speed):
            if not self.is_master_unlocked:
                self.show_auth_locked_warning()
            else:
                self.set_speed_value(target_speed, speed_dialog)

        btn_s30 = ctk.CTkButton(
            right_col, text="⚡ Speed 30", command=lambda: trigger_pro_speed(30),
            width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#d35400", hover_color="#b54600"
        )
        btn_s30.pack(pady=(0, 8), fill="x")

        btn_s40 = ctk.CTkButton(
            right_col, text="⚡ Speed 40", command=lambda: trigger_pro_speed(40),
            width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#d35400", hover_color="#b54600"
        )
        btn_s40.pack(pady=(0, 8), fill="x")

        btn_s50 = ctk.CTkButton(
            right_col, text="🚀 Ultra Speed", command=lambda: trigger_pro_speed(50),
            width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#c92a2a", hover_color="#a61e1e"
        )
        btn_s50.pack(pady=(0, 8), fill="x")

    def set_speed_value(self, val, dialog_window):
        self.current_speed = val
        self.btn_speed.configure(text=f"⚡ {self.current_speed}")
        self.log_boxes(f"Kecepatan scanning diatur ke Speed {self.current_speed}.", "SPEED UPDATED", "green")
        if dialog_window:
            dialog_window.destroy()

    def check_scan_readiness(self):
        has_source = self.is_private_active or len(self.imported_domains) > 0
        has_tld = (self.filter_entry.get().strip() != "") or self.is_point_private

        if has_source and has_tld:
            self.btn_scan.configure(state="normal", text="🔓 Scan", fg_color="#2b8a3e", hover_color="#216e31")
        else:
            self.btn_scan.configure(state="disabled", text="🔒 Scan", fg_color="#555555")

    def show_tld_picker_popup(self):
        tld_dialog = ctk.CTkToplevel(self)
        tld_dialog.title("Pilih Target TLD Domain")
        tld_dialog.geometry("540x480")
        tld_dialog.resizable(False, False)
        tld_dialog.attributes("-topmost", True)

        lbl_title = ctk.CTkLabel(tld_dialog, text="🎯 Pilih TLD Domain Target", font=("Segoe UI", 15, "bold"))
        lbl_title.pack(pady=(12, 4))

        search_frame = ctk.CTkFrame(tld_dialog, fg_color="transparent")
        search_frame.pack(fill="x", padx=15, pady=(0, 8))

        search_entry = ctk.CTkEntry(search_frame, placeholder_text="🔍 Cari TLD (cth: .id, .com, .Private)...", height=32, font=("Segoe UI", 12))
        search_entry.pack(fill="x", expand=True)

        scroll_frame = ctk.CTkScrollableFrame(tld_dialog, width=500, height=360)
        scroll_frame.pack(padx=15, pady=(0, 10), fill="both", expand=True)

        def select_tld(selected_tld):
            if selected_tld == ".Private":
                if not self.is_master_unlocked:
                    self.show_auth_locked_warning()
                    return
                
                self.is_point_private = True
                self.filter_entry.configure(state="normal")
                self.filter_entry.delete(0, "end")
                self.filter_entry.insert(0, ".Private (All TLD)")
                self.filter_entry.configure(state="disabled")
                self.btn_point.configure(text="Point (.Private)", fg_color="#1f538d", hover_color="#143c68")
                self.log_boxes("Point Mode: .Private diaktifkan (Scan semua TLD).", "POINT ACCESS", "green")
                tld_dialog.destroy()
                self.check_scan_readiness()
            else:
                self.is_point_private = False
                self.filter_entry.configure(state="normal")
                self.filter_entry.delete(0, "end")
                self.filter_entry.insert(0, selected_tld)
                self.filter_entry.configure(state="disabled")
                self.btn_point.configure(text=f"Point ({selected_tld})", fg_color="#d35400", hover_color="#b54600")
                tld_dialog.destroy()
                self.check_scan_readiness()

        buttons_ref = []

        def render_buttons(filter_text=""):
            for btn in buttons_ref:
                btn.destroy()
            buttons_ref.clear()

            clean_query = filter_text.strip().lower()
            filtered_list = [t for t in TLD_LIST if clean_query in t.lower()] if clean_query else TLD_LIST

            if not filtered_list:
                no_res = ctk.CTkLabel(scroll_frame, text="TLD tidak ditemukan.", font=("Segoe UI", 12), text_color="gray")
                no_res.pack(pady=20)
                buttons_ref.append(no_res)
                return

            columns = 4
            grid_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            grid_frame.pack(fill="x", expand=True)
            buttons_ref.append(grid_frame)

            for idx, tld_item in enumerate(filtered_list):
                row_idx = idx // columns
                col_idx = idx % columns

                if tld_item == ".Private":
                    btn = ctk.CTkButton(
                        grid_frame, text="🔒 .Private", 
                        command=lambda t=tld_item: select_tld(t),
                        width=110, height=BTN_HEIGHT, font=("Consolas", 11, "bold"),
                        fg_color="#c92a2a", hover_color="#a61e1e", text_color="white"
                    )
                else:
                    btn = ctk.CTkButton(
                        grid_frame, text=tld_item, 
                        command=lambda t=tld_item: select_tld(t),
                        width=110, height=BTN_HEIGHT, font=("Consolas", 11, "bold"),
                        fg_color="#1f538d", hover_color="#143c68", text_color="white"
                    )
                btn.grid(row=row_idx, column=col_idx, padx=4, pady=4, sticky="ew")

        render_buttons()
        search_entry.bind("<KeyRelease>", lambda event: render_buttons(search_entry.get()))

    def handle_private_button(self):
        if self.is_private_active:
            self.is_private_active = False
            self.btn_private.configure(text="🔐 Private", fg_color="#c92a2a", hover_color="#a61e1e")
            self.log_boxes("Mode Private dinonaktifkan.", "INFO", "yellow")
            self.check_scan_readiness()
            return

        if not self.is_master_unlocked:
            self.show_auth_locked_warning()
            return

        self.is_private_active = True
        self.imported_domains = []
        self.btn_private.configure(text="🔒 Private", fg_color="#1f538d", hover_color="#143c68")
        self.log_boxes("Auth Key Benar! Mode Private GitHub diaktifkan.", "SUCCESS", "green")
        self.check_scan_readiness()

    def import_external_file(self):
        file_path = filedialog.askopenfilename(
            title="Pilih File Domain (.txt / .csv)",
            filetypes=[
                ("Supported Files", "*.txt;*.csv"),
                ("Text Files", "*.txt"),
                ("CSV Files", "*.csv"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            try:
                extracted_domains = []
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line_str = line.strip()
                        if not line_str or line_str.startswith("#"):
                            continue
                        if file_path.lower().endswith(".csv"):
                            parts = [p.strip() for p in line_str.replace(";", ",").split(",") if p.strip()]
                            for part in parts:
                                if "." in part and not part.startswith("#"):
                                    extracted_domains.append(part)
                        else:
                            extracted_domains.append(line_str)

                if not extracted_domains:
                    self.log_boxes("File yang diimpor kosong atau tidak berisi format domain valid!", "ERROR", "red")
                    return
                
                self.imported_domains = list(dict.fromkeys(extracted_domains))
                self.is_private_active = False
                self.btn_private.configure(text="🔐 Private", fg_color="#c92a2a", hover_color="#a61e1e")
                
                self.log_boxes(f"Berhasil mengimpor {len(self.imported_domains)} domain dari file ({os.path.basename(file_path)}).", "IMPORT", "green")
                self.check_scan_readiness()
            except Exception as e:
                self.log_boxes(f"Gagal membaca file: {e}", "ERROR", "red")

    def show_ns_checker_popup(self):
        ns_dialog = ctk.CTkToplevel(self)
        ns_dialog.title("Domain Checker")
        ns_dialog.geometry("680x520")
        ns_dialog.resizable(False, False)
        ns_dialog.attributes("-topmost", True)

        lbl_title = ctk.CTkLabel(ns_dialog, text="🌐 Domain Checker", font=("Segoe UI", 16, "bold"))
        lbl_title.pack(pady=(10, 4))

        info_textbox = ctk.CTkTextbox(ns_dialog, width=640, height=340, font=("Consolas", 11), fg_color="#000000", text_color="#00FF66")
        info_textbox.pack(padx=20, pady=(2, 6))
        info_textbox.insert("0.0", "Status: Ready.\nMasukkan nama domain di bawah, lalu klik tombol cek record yang diinginkan.\n\n")
        info_textbox.configure(state="disabled")

        global_dns_servers = [
            {"country": "🇺🇸 San Francisco CA, United States (OpenDNS)", "resolver": "208.67.222.222"},
            {"country": "🇺🇸 Mountain View CA, United States (Google)", "resolver": "8.8.8.8"},
            {"country": "🇺🇸 Berkeley, US (Quad9)", "resolver": "9.9.9.9"},
            {"country": "🇺🇸 Cambridge, United States (Akamai)", "resolver": "172.226.0.1"},
            {"country": "🇺🇸 Ashburn, United States (Quad9)", "resolver": "149.112.112.112"},
            {"country": "🇺🇸 San Francisco, United States (CloudFlare)", "resolver": "1.1.1.1"},
            {"country": "🇳🇱 Amsterdam, Belanda (DNS.Watch)", "resolver": "84.200.69.80"},
            {"country": "🇩🇪 Frankfurt am Main, Jerman (SecDNS)", "resolver": "185.95.218.42"},
            {"country": "🇷🇺 St. Petersburg, Rusia (Yandex)", "resolver": "77.88.8.8"},
            {"country": "🇸🇬 Singapura, Singapura (Tefincom)", "resolver": "165.21.100.88"},
            {"country": "🇯🇵 Tokyo, Jepang (Google JP)", "resolver": "8.8.4.4"}
        ]

        def is_valid_ipv4(ip_str):
            parts = ip_str.split('.')
            if len(parts) != 4:
                return False
            for p in parts:
                if not p.isdigit() or not (0 <= int(p) <= 255):
                    return False
            return True

        def run_global_dns_query(query_type):
            domain_name = domain_entry.get().strip()
            if not domain_name:
                info_textbox.configure(state="normal")
                info_textbox.delete("0.0", "end")
                info_textbox.insert("0.0", "❌ Error: Masukkan nama domain terlebih dahulu!")
                info_textbox.configure(state="disabled")
                return

            domain_clean = domain_name.replace("http://", "").replace("https://", "").strip("/").split('/')[0]
            
            info_textbox.configure(state="normal")
            info_textbox.delete("0.0", "end")
            info_textbox.insert("0.0", f"Memeriksa {query_type} Record untuk '{domain_clean}' di {len(global_dns_servers)} Server Global...\n\n")
            info_textbox.configure(state="disabled")

            def worker():
                results_output = [f"Target: {domain_clean} | Record Type: {query_type}\n" + "="*75 + "\n"]
                def query_single_server(server_info):
                    country = server_info["country"]
                    ip_dns = server_info["resolver"]
                    try:
                        ps_cmd = f"nslookup -type={query_type} {domain_clean} {ip_dns}"
                        process = subprocess.Popen(["powershell", "-Command", ps_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        stdout, stderr = process.communicate()
                        output = stdout if stdout else stderr
                        
                        resolved_values = []
                        for line in output.splitlines():
                            l_stripped = line.strip()
                            if not l_stripped or any(x in l_stripped for x in ["Servers:", "Address:", "Name:", "Aliases:"]):
                                continue
                            if domain_clean.lower() in l_stripped.lower():
                                continue
                            if ":" in l_stripped:
                                val = l_stripped.split(":")[-1].strip()
                                if val and val != domain_clean:
                                    resolved_values.append(val)
                            else:
                                resolved_values.append(l_stripped)

                        if query_type == "A":
                            filtered_ips = []
                            for val in resolved_values:
                                clean_ip = val.split()[0]
                                if is_valid_ipv4(clean_ip) and clean_ip not in filtered_ips:
                                    filtered_ips.append(clean_ip)
                            resolved_values = filtered_ips

                        result_str = " | ".join(resolved_values) if resolved_values else "Tidak ada respons / Record kosong"
                        status_mark = "✔" if resolved_values and "error" not in result_str.lower() else "✘"
                        return f"📍 {country}\n   └─ [{status_mark}] {result_str}\n"
                    except Exception:
                        return f"📍 {country}\n   └─ [✘] Gagal Query\n"

                threads = []
                server_results = ["" for _ in global_dns_servers]
                for idx, s_info in enumerate(global_dns_servers):
                    t = threading.Thread(target=lambda i, s: __import__('operator').setitem(server_results, i, query_single_server(s)), args=(idx, s_info), daemon=True)
                    threads.append(t)
                    t.start()
                for t in threads:
                    t.join()

                final_text = "".join(results_output + server_results)
                info_textbox.configure(state="normal")
                info_textbox.delete("0.0", "end")
                info_textbox.insert("0.0", final_text)
                info_textbox.see("0.0")
                info_textbox.configure(state="disabled")

            threading.Thread(target=worker, daemon=True).start()

        input_frame = ctk.CTkFrame(ns_dialog, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=(0, 8))

        domain_entry = ctk.CTkEntry(input_frame, placeholder_text="Input Domain Target ...", width=640, height=BTN_HEIGHT, font=("Consolas", 11))
        domain_entry.pack(side="left", fill="x", expand=True)
        domain_entry.bind("<Return>", lambda event: run_global_dns_query("NS"))

        btn_action_frame = ctk.CTkFrame(ns_dialog, fg_color="transparent")
        btn_action_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(btn_action_frame, text="NS Check", command=lambda: run_global_dns_query("NS"), width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#2b8a3e", hover_color="#216e31", text_color="white").pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_action_frame, text="A Check", command=lambda: run_global_dns_query("A"), width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#1f538d", hover_color="#143c68", text_color="white").pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_action_frame, text="CNAME", command=lambda: run_global_dns_query("CNAME"), width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#d35400", hover_color="#b54600", text_color="white").pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_action_frame, text="❌ Exit", command=ns_dialog.destroy, width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#c92a2a", hover_color="#a61e1e", text_color="white").pack(side="right")

    def show_netstat_popup(self):
        net_dialog = ctk.CTkToplevel(self)
        net_dialog.title("JKSY Terminal & Diagnostics")
        net_dialog.geometry("680x520")
        net_dialog.resizable(False, False)
        net_dialog.attributes("-topmost", True)

        lbl_title = ctk.CTkLabel(net_dialog, text="💻 JKSY Interactive Terminal", font=("Segoe UI", 16, "bold"))
        lbl_title.pack(pady=(10, 4))

        cmd_textbox = ctk.CTkTextbox(net_dialog, width=640, height=340, font=("Consolas", 11), fg_color="#000000", text_color="#00FF66")
        cmd_textbox.pack(padx=20, pady=(2, 6))
        cmd_textbox.insert("0.0", "Terminal jksy.v.2.1.2 ready.\nKetik perintah pada kolom di bawah atau gunakan tombol pintasan.\n\n")
        cmd_textbox.configure(state="disabled")

        def run_command_in_box(command_str):
            if not command_str:
                return
            cmd_textbox.configure(state="normal")
            cmd_textbox.delete("0.0", "end")
            cmd_textbox.insert("0.0", f"Executing: {command_str}...\n\n")
            cmd_textbox.configure(state="disabled")
            
            def worker():
                try:
                    formatted_cmd = "Get-ChildItem | Select-Object Mode, LastWriteTime, Length, Name | Format-Table -AutoSize" if command_str.strip().lower() in ["ls", "dir"] else command_str
                    process = subprocess.Popen(["powershell", "-Command", formatted_cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    stdout, stderr = process.communicate()
                    output = stdout if stdout else stderr
                    final_output = "\n".join([line.rstrip() for line in output.splitlines() if line.strip() != ""])

                    cmd_textbox.configure(state="normal")
                    cmd_textbox.delete("0.0", "end")
                    cmd_textbox.insert("0.0", final_output if final_output else "Perintah selesai dijalankan tanpa output.")
                    cmd_textbox.see("end")
                    cmd_textbox.configure(state="disabled")
                except Exception as e:
                    cmd_textbox.configure(state="normal")
                    cmd_textbox.delete("0.0", "end")
                    cmd_textbox.insert("0.0", f"Error menjalankan perintah: {e}")
                    cmd_textbox.configure(state="disabled")

            threading.Thread(target=worker, daemon=True).start()

        input_frame = ctk.CTkFrame(net_dialog, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=(0, 8))

        cmd_entry = ctk.CTkEntry(input_frame, placeholder_text="Input Prompt ...", width=520, height=BTN_HEIGHT, font=("Consolas", 11))
        cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        cmd_entry.bind("<Return>", lambda event: run_command_in_box(cmd_entry.get().strip()))

        ctk.CTkButton(input_frame, text="Run", command=lambda: run_command_in_box(cmd_entry.get().strip()), width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#1f538d", hover_color="#143c68", text_color="white").pack(side="right")

        btn_action_frame = ctk.CTkFrame(net_dialog, fg_color="transparent")
        btn_action_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(btn_action_frame, text="Ping", command=lambda: run_command_in_box("ping 8.8.8.8 -n 5"), width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#2b8a3e", hover_color="#216e31", text_color="white").pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_action_frame, text="Tracert", command=lambda: run_command_in_box("tracert 8.8.8.8"), width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#1f538d", hover_color="#143c68", text_color="white").pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_action_frame, text="Netstat", command=lambda: run_command_in_box("netstat -an"), width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#d35400", hover_color="#b54600", text_color="white").pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_action_frame, text="❌ Exit", command=net_dialog.destroy, width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#c92a2a", hover_color="#a61e1e", text_color="white").pack(side="right")

    def update_realtime_clock(self):
        while True:
            try:
                now = datetime.datetime.now()
                time_str = now.strftime("%H:%M:%S")
                date_str = now.strftime("%d-%m-%Y")
                os_name = f"{platform.system()} {platform.release()}"
                
                if psutil:
                    cpu_info = platform.uname().processor or "Intel/AMD Processor"
                    ram_total = round(psutil.virtual_memory().total / (1024.0 ** 3), 1)
                    ram_info = f"{ram_total} GB"
                    disk_usage = shutil.disk_usage("C:" if os.name == 'nt' else "/")
                    ssd_total = round(disk_usage.total / (1024.0 ** 3), 1)
                    ssd_info = f"{ssd_total} GB"
                else:
                    cpu_info = "Standard CPU"
                    ram_info = "N/A"
                    ssd_info = "N/A"

                info_text = (
                    f"VERSION : JKSY-V2.1.2\n"
                    f"TIME    : {time_str} WIB\n"
                    f"DATE    : {date_str}\n"
                    f"OS      : {os_name}\n"
                    f"CPU     : {cpu_info[:25]}\n"
                    f"RAM     : {ram_info}\n"
                    f"SSD     : {ssd_info}\n"
                    f"CREATOR : JOKESKYLS\n"
                    f"TELEGRAM: @nazisme1930"
                )
                self.box_info.configure(state="normal")
                self.box_info.delete("0.0", "end")
                self.box_info.insert("0.0", info_text)
                self.box_info.configure(state="disabled")
            except Exception:
                pass
            time.sleep(1)

    def log_boxes(self, domain_text, status_text, tag="normal"):
        self.box_domain.configure(state="normal")
        self.box_domain.insert("end", domain_text + "\n")
        self.box_domain.see("end")
        self.box_domain.configure(state="disabled")

        self.box_status.configure(state="normal")
        self.box_status._textbox.insert("end", status_text + "\n", tag)
        self.box_status.see("end")
        self.box_status.configure(state="disabled")

    def update_counter_display(self):
        self.counter_label.configure(text=f"📈 Total Discan: {self.scanned_count}")

    def start_scanning_thread(self):
        if not self.is_private_active and not self.imported_domains:
            self.log_boxes("❌ Pilih sumber scan terlebih dahulu (Import file atau Unlock Private)!", "ERROR", "red")
            return

        if not self.is_point_private and not self.filter_entry.get().strip():
            self.log_boxes("❌ Pilih TLD atau Private terlebih dahulu melalui tombol Point!", "ERROR", "red")
            return

        self.stop_requested = False
        self.is_scanning = True
        self.scanned_count = 0
        self.update_counter_display()
        self.progress_bar.set(0.0)
        self.progress_label.configure(text="0%")
        
        self.btn_scan.configure(state="disabled", text="Scanning...")
        self.btn_stop.configure(state="normal")
        
        filter_keyword = self.filter_entry.get().strip()
        filter_info = f" [Filter: '{filter_keyword}']" if (filter_keyword and not self.is_point_private) else (" [Mode: ALL TLD]" if self.is_point_private else "")
        
        if self.is_private_active:
            self.log_boxes(f"--- START SCAN (MODE: PRIVATE GITHUB){filter_info} [SPEED: {self.current_speed}] ---", "PROCESS", "yellow")
        elif self.imported_domains:
            self.log_boxes(f"--- START SCAN (MODE: FILE Lokal){filter_info} [SPEED: {self.current_speed}] ---", "PROCESS", "yellow")
        
        threading.Thread(target=lambda: asyncio.run(self.run_scanner_async()), daemon=True).start()

    def stop_scanning(self):
        if self.is_scanning:
            self.stop_requested = True
            self.log_boxes("PROCESS STOPPED BY USER", "ABORTED", "yellow")
            self.btn_stop.configure(state="disabled")

    async def check_domain(self, session, domain, semaphore, filter_keyword, total_domains, results_list):
        if self.stop_requested:
            return

        url = domain.strip().lower()
        if not url: return

        if filter_keyword and not self.is_point_private:
            clean_filter = filter_keyword.strip().lower()
            if not clean_filter.startswith('.'):
                clean_filter = f".{clean_filter}"
            if not url.endswith(clean_filter):
                return

        full_url = url if url.startswith(('http://', 'https://')) else f"http://{url}"

        async with semaphore:
            if self.stop_requested:
                return
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                async with session.head(full_url, timeout=10, headers=headers, allow_redirects=True) as response:
                    status, tag_color = "BLOCK", "red"
            except Exception:
                status, tag_color = "GET", "green"
                results_list.append(url)

            if not self.stop_requested:
                self.log_boxes(url, f"[{status}]", tag_color)
                self.scanned_count += 1
                self.after(0, self.update_counter_display)

                progress_val = self.scanned_count / total_domains
                percent_val = int(progress_val * 100)
                self.after(0, lambda v=progress_val, p=percent_val: [
                    self.progress_bar.set(v),
                    self.progress_label.configure(text=f"{p}%")
                ])

    async def run_scanner_async(self):
        filter_keyword = self.filter_entry.get().strip()
        scanned_results = []

        if self.is_private_active:
            self.log_boxes("Mengambil data dari GitHub Private Anda...", "FETCHING", "normal")
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(GITHUB_RAW_URL, timeout=15) as resp:
                        if resp.status != 200:
                            self.log_boxes(f"Gagal koneksi ke GitHub (Status: {resp.status})", "ERROR", "red")
                            self.reset_button_state()
                            return
                        text_content = await resp.text()
                domains = [line.strip() for line in text_content.splitlines() if line.strip() and not line.startswith("#")]
            except Exception as e:
                self.log_boxes(f"Error mengambil data GitHub: {e}", "ERROR", "red")
                self.reset_button_state()
                return
        elif self.imported_domains:
            self.log_boxes("Menggunakan data dari file lokal...", "LOADED", "normal")
            domains = self.imported_domains
        else:
            self.log_boxes("❌ Sumber domain tidak valid!", "ERROR", "red")
            self.reset_button_state()
            return

        if self.stop_requested:
            self.reset_button_state()
            return

        total = len(domains)
        if total == 0:
            self.log_boxes("Tidak ada domain ditemukan!", "ERROR", "red")
            self.reset_button_state()
            return

        self.log_boxes(f"Memulai pengecekan {total} domain (Speed {self.current_speed})...", "RUNNING", "yellow")
        semaphore = asyncio.Semaphore(self.current_speed)

        async with aiohttp.ClientSession() as session:
            tasks = [
                self.check_domain(session, d, semaphore, filter_keyword, total, scanned_results) 
                for d in domains
            ]
            for task in asyncio.as_completed(tasks):
                if self.stop_requested:
                    break
                await task
        
        if self.stop_requested:
            self.log_boxes("Proses dihentikan.", "STOPPED", "yellow")
        else:
            self.log_boxes("Scanning & filtering selesai!", "SUCCESS", "green")
            self.after(0, lambda: [self.progress_bar.set(1.0), self.progress_label.configure(text="100%")])
            
            try:
                existing_results = []
                if os.path.exists("DGO-JKSY-NOTUSE.txt"):
                    with open("DGO-JKSY-NOTUSE.txt", "r", encoding="utf-8") as f_in:
                        existing_results = [line.strip() for line in f_in.readlines() if line.strip()]
                
                combined_results = list(dict.fromkeys(existing_results + scanned_results))
                with open("DGO-JKSY-NOTUSE.txt", "w", encoding="utf-8") as f_out:
                    f_out.write("\n".join(combined_results) + ("\n" if combined_results else ""))
            except Exception:
                pass

        self.reset_button_state()

    def reset_button_state(self):
        self.is_scanning = False
        self.stop_requested = False
        self.check_scan_readiness()
        self.btn_stop.configure(state="disabled")

    def show_results_popup(self):
        notuse_count = self.count_results("DGO-JKSY-NOTUSE.txt")
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Check Box")
        dialog.geometry("500x520")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)

        lbl = ctk.CTkLabel(dialog, text="📁 Box Domain Ready", font=("Segoe UI", 18, "bold"))
        lbl.pack(pady=(15, 5))

        summary_frame = ctk.CTkFrame(dialog, fg_color=("#e9ecef", "#1a1a1a"), corner_radius=8)
        summary_frame.pack(fill="x", padx=20, pady=10)

        lbl_notuse = ctk.CTkLabel(summary_frame, text=f"🟢 Domain Ready (GET): {notuse_count}", font=("Segoe UI", 13, "bold"), text_color=("#2b8a3e", "#00FF66"))
        lbl_notuse.pack(anchor="center", pady=10)

        notuse_textbox = ctk.CTkTextbox(dialog, width=460, height=280, font=("Consolas", 12), fg_color=("#f0f0f0", "#000000"), text_color=("#008000", "#00FF66"))
        notuse_textbox.pack(padx=20, pady=(0, 10))

        file_path = "DGO-JKSY-NOTUSE.txt"

        def refresh_textbox_content():
            notuse_textbox.configure(state="normal")
            notuse_textbox.delete("0.0", "end")
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        notuse_textbox.insert("0.0", content if content else "File kosong atau belum ada data domain ready.")
                except Exception as e:
                    notuse_textbox.insert("0.0", f"Gagal membaca file: {e}")
            else:
                notuse_textbox.insert("0.0", "Domain belum ditemukan. Lakukan scan terlebih dahulu.")
            notuse_textbox.configure(state="disabled")

        refresh_textbox_content()

        action_btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        action_btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(action_btn_frame, text="💾 Save", command=self.save_results_file, width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#2b8a3e", hover_color="#216e31", text_color="white").pack(side="left")

        def clear_checkbox_history():
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            refresh_textbox_content()
            lbl_notuse.configure(text="🟢 Domain Ready (GET): 0")

        ctk.CTkButton(action_btn_frame, text="🗑️ Clear", command=clear_checkbox_history, width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#c92a2a", hover_color="#a61e1e", text_color="white").pack(side="left", padx=(10, 0))
        ctk.CTkButton(action_btn_frame, text="Tutup", command=dialog.destroy, width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), text_color="white").pack(side="right")

    def save_results_file(self):
        source_file = "DGO-JKSY-NOTUSE.txt"
        if not os.path.exists(source_file):
            return
        file_selected = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")], initialfile="Domain_Ready_JKSY.txt", title="Simpan File Hasil Domain")
        if file_selected:
            try:
                shutil.copy(source_file, file_selected)
            except Exception:
                pass

    def count_results(self, filename):
        if os.path.exists(filename):
            with open(filename, 'r', encoding="utf-8") as f:
                return len(f.readlines())
        return 0

    def clear_files(self):
        for file in ["DGO-JKSY-USE.txt", "DGF-JKSY-NOTUSE.txt"]:
            if os.path.exists(file): 
                os.remove(file)
                
        self.imported_domains = []  
        self.is_private_active = False
        self.is_point_private = False
        self.btn_private.configure(text="🔐 Private", fg_color="#c92a2a", hover_color="#a61e1e")
        self.btn_point.configure(text="Point", fg_color="#d35400", hover_color="#b54600")
        
        self.filter_entry.configure(state="normal")
        self.filter_entry.delete(0, "end")
        self.filter_entry.configure(state="disabled")

        self.btn_scan.configure(state="disabled", text="🔒 Scan", fg_color="#555555")
        self.scanned_count = 0
        self.update_counter_display()
        self.progress_bar.set(0.0)
        self.progress_label.configure(text="0%")
        
        self.box_domain.configure(state="normal")
        self.box_domain.delete("0.0", "end")
        self.box_domain.configure(state="disabled")

        self.box_status.configure(state="normal")
        self.box_status._textbox.delete("0.0", "end")
        self.box_status.configure(state="disabled")

        self.log_boxes("History & UI Refreshed.\n", "CLEARED", "yellow")

        # --- PROTEKSI: DIKUNCI AGAR TIDAK BISA DIBUKA LANGSUNG DARI TERMINAL ---
if __name__ == "__main__":
    from tkinter import messagebox, sys
    root = ctk.CTk()
    root.withdraw()
    messagebox.showerror(
        "Access Denied", 
        "Modul Takeover terkunci!\nModul ini hanya dapat dijalankan secara sah melalui launcher utama (aplikasi.py)."
    )
    root.destroy()
    sys.exit()