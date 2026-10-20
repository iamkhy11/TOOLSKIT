import time
import os
import hashlib
import hmac
import base64
import platform
import datetime
import shutil
import socket
import threading
import urllib.request
import json
import webbrowser
import importlib.util
import subprocess
import sys
from io import BytesIO
from tkinter import messagebox
from PIL import Image
import customtkinter as ctk

# Import dinamis untuk modul-modul di dalam folder toolskit (mendukung tanda hubung '-')
def load_tool_module(filename):
    path = os.path.join(os.path.dirname(__file__), "toolskit", filename)
    spec = importlib.util.spec_from_file_location(filename.replace("-", "_").replace(".py", ""), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Memuat modul Takeover, DDoS, dan Finder (f-jksy)
gui_jksy = load_tool_module("tk-jksy.py")
ddos_jksy = load_tool_module("d-jksy.py")
finder_jksy = load_tool_module("f-jksy.py")
bf_jksy = load_tool_module("bf-jksy.py")
j_ai = load_tool_module("j-ai.py")
ws_jksy = load_tool_module("ws-jksy.py")
au_jksy = load_tool_module("au-jksy.py")
tf_jksy = load_tool_module("tf-jksy.py")

try:
    import psutil
except ImportError:
    psutil = None

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

internal_stk = "04789992e0eed99a36184d3b3a59b82f"
_enc_license = "amtzeV9saWNlbnNlLmRhdA=="
LICENSE_FILE = base64.b64decode(_enc_license).decode('utf-8')
TRIAL_DURATION = 60 * 5
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jksy_user_settings.json')
READY_TOOLS = ('Takeover', 'Finder', 'Scanner', 'Brute Force', 'Ddos', 'J Ai', 'Web Shell', 'Authority', 'Traffic')
LOCK_COLOR = '#991B1B'
UNLOCK_COLOR = '#2b8a3e'

def validate_jksy_auth(candidate):
    """Compare PBKDF2 hash; do not keep plaintext key in the source."""
    salt = bytes.fromhex('a51477c90d6283b4e932bc1465f6ae82')
    expected = bytes.fromhex('761d7544d567650461f340dfaa7ad7b6d72d65e48ac8eff9924c71b84b9dce56')
    actual = hashlib.pbkdf2_hmac('sha256', candidate.encode('utf-8'), salt, 240000)
    return hmac.compare_digest(actual, expected)


BTN_WIDTH = 80
BTN_HEIGHT = 28

MONTH_NAMES_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}

class JKSYLauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("JKSY Tools Kit v6.9.12 - Authentication Launcher")
        self.geometry("780x560")
        self.resizable(False, False)

        self.is_premium = False
        self.login_mode = None
        self.trial_after_id = None
        self.geo_info = "Fetching..."
        self.public_ip = "Fetching..."
        self.clock_running = False
        self.profile = {'name': '', 'age': '', 'icon': '?'}
        self.preferences = {'graphics': 'Medium', 'fps': '60'}
        self.unlocked_tools = set()  # Unlock berlaku per sesi, tidak disimpan ke disk.
        self.tool_buttons = {}
        self.load_user_settings()

        self.init_trial_system()
        self.build_login_frame()
        threading.Thread(target=self.fetch_network_geo_info, daemon=True).start()

    def load_user_settings(self):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            profile = data.get('profile', {})
            preferences = data.get('preferences', {})
            if isinstance(profile, dict):
                for key in self.profile:
                    if isinstance(profile.get(key), str):
                        self.profile[key] = profile[key]
            if isinstance(preferences, dict):
                if preferences.get('graphics') in ('Low', 'Medium', 'High', 'Ultra'):
                    self.preferences['graphics'] = preferences['graphics']
                if str(preferences.get('fps')) in ('30', '60', '90', '120'):
                    self.preferences['fps'] = str(preferences['fps'])
        except (OSError, ValueError, TypeError):
            pass

    def save_user_settings(self):
        data = {'profile': self.profile, 'preferences': self.preferences}
        temporary = SETTINGS_FILE + '.tmp'
        with open(temporary, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(temporary, SETTINGS_FILE)

    def _front_window(self, parent):
        """Create a child window in front without locking other JKSY windows."""
        window = ctk.CTkToplevel(parent)
        try:
            window.transient(parent)
        except Exception:
            pass

        def promote():
            if not window.winfo_exists():
                return
            try:
                window.lift()
                window.attributes('-topmost', True)
                window.focus_force()
                # Only temporarily topmost, so tools can still be multitasked.
                window.after(650, lambda: window.attributes('-topmost', False)
                             if window.winfo_exists() else None)
            except Exception:
                pass

        window.after(60, promote)
        return window

    def show_setup(self):
        # Dashboard tetap terlihat agar Setup dapat digunakan secara multitasking.
        setup = self._front_window(self)
        setup.title('JKSY • Setup Center')
        setup.geometry('480x430')
        setup.resizable(False, False)
        setup.configure(fg_color='#111111')
        def close():
            setup.destroy()
        setup.protocol('WM_DELETE_WINDOW', close)
        ctk.CTkLabel(setup, text='⚙️ JKSY SETUP CENTER', font=('Segoe UI', 20, 'bold'),
                     text_color='#00FF66').pack(pady=(20, 4))
        ctk.CTkLabel(setup, text='Kelola profil, preferensi, dan akses tools',
                     text_color='#AAAAAA').pack(pady=(0, 15))
        for title, desc, command in (
            ('Edit Profile', 'Nama, usia, dan ikon pengguna', lambda: self.open_edit_profile(setup)),
            ('Setting', 'API AI, grafik, dan FPS', lambda: self.open_app_settings(setup)),
            ('Unlock Auth Key', 'Pilih tools yang akan dibuka', lambda: self.open_unlock_setup(setup)),
        ):
            panel = ctk.CTkFrame(setup, fg_color='#1a1a1a', corner_radius=8)
            panel.pack(fill='x', padx=22, pady=5)
            ctk.CTkButton(panel, text=title, command=command, width=160,
                          fg_color='#1f538d', hover_color='#143c68').pack(side='left', padx=12, pady=12)
            ctk.CTkLabel(panel, text=desc, text_color='#BBBBBB', font=('Segoe UI', 11)).pack(side='left')
        ctk.CTkButton(setup, text='← Kembali', command=close, fg_color='#991B1B',
                      width=135).pack(side='bottom', pady=18)

    def open_edit_profile(self, parent):
        dialog = self._front_window(parent)
        dialog.title('JKSY • Edit Profile')
        dialog.geometry('390x395')
        dialog.resizable(False, False)
        ctk.CTkLabel(dialog, text='Edit Profile', font=('Segoe UI', 18, 'bold'),
                     text_color='#00FF66').pack(pady=(18, 12))
        ctk.CTkLabel(dialog, text='Nama', anchor='w').pack(fill='x', padx=28)
        name = ctk.CTkEntry(dialog, placeholder_text='Input Nama', width=330)
        name.pack(padx=28, pady=(3, 9))
        name.insert(0, self.profile['name'])
        ctk.CTkLabel(dialog, text='Usia', anchor='w').pack(fill='x', padx=28)
        age = ctk.CTkEntry(dialog, placeholder_text='Input Usia', width=330)
        age.pack(padx=28, pady=(3, 9))
        age.insert(0, self.profile['age'])
        ctk.CTkLabel(dialog, text='Pick • Icon Profil', anchor='w').pack(fill='x', padx=28)
        selected = ctk.StringVar(value=self.profile['icon'] if self.profile['icon'] in
            ('?', '👤', '🦊', '🐺', '🦁', '🐼', '🐉', '⚡', '💎', '👑', '🎮', '🛡️', '🌙') else '?')
        ctk.CTkOptionMenu(dialog, variable=selected, values=[
            '?', '👤', '🦊', '🐺', '🦁', '🐼', '🐉', '⚡', '💎', '👑', '🎮', '🛡️', '🌙'],
            width=330).pack(padx=28, pady=(3, 17))
        def save():
            username = name.get().strip()
            years = age.get().strip()
            if len(username) > 40 or (years and (not years.isdigit() or not 1 <= int(years) <= 120)):
                messagebox.showerror('Profile', 'Nama maksimal 40 karakter; usia harus 1–120.', parent=dialog)
                return
            self.profile = {'name': username, 'age': years, 'icon': selected.get()}
            try:
                self.save_user_settings()
            except OSError as exc:
                messagebox.showerror('Profile', f'Gagal menyimpan: {exc}', parent=dialog)
                return
            messagebox.showinfo('Profile', 'Profil berhasil disimpan.', parent=dialog)
            dialog.destroy()
        ctk.CTkButton(dialog, text='Save', command=save, fg_color=UNLOCK_COLOR,
                      width=150).pack(pady=7)

    def show_profile(self):
        """Tampilkan profil dalam jendela terpisah, dashboard tetap terlihat."""
        dialog = self._front_window(self)
        dialog.title('JKSY • User Profile')
        dialog.geometry('430x430')
        dialog.resizable(False, False)
        dialog.configure(fg_color='#111111')

        def close_profile():
            dialog.destroy()

        dialog.protocol('WM_DELETE_WINDOW', close_profile)
        ctk.CTkLabel(dialog, text='USER PROFILE', font=('Segoe UI', 19, 'bold'),
                     text_color='#00FF66').pack(pady=(24, 8))
        icon = self.profile.get('icon') or '?'
        # Pengguna baru yang belum mengatur profil memperoleh ikon '?' default.
        if not self.profile.get('name') and not self.profile.get('age') and icon == '👤':
            icon = '?'
        icon_panel = ctk.CTkFrame(dialog, width=110, height=110, corner_radius=55,
                                  fg_color='#202020', border_width=2, border_color='#2b8a3e')
        icon_panel.pack(pady=(5, 17))
        icon_panel.pack_propagate(False)
        ctk.CTkLabel(icon_panel, text=icon, font=('Segoe UI Emoji', 54, 'bold'),
                     text_color='#00FF66').place(relx=0.5, rely=0.5, anchor='center')

        info = ctk.CTkFrame(dialog, fg_color='#191919', corner_radius=10)
        info.pack(fill='x', padx=30, pady=(0, 16))
        rows = [
            ('Nama', self.profile.get('name') or 'Bot'),
            ('Usia', self.profile.get('age') or 'Bot'),
            ('Status', 'Premium' if self.is_premium else 'Trial'),
        ]
        for label, value in rows:
            row = ctk.CTkFrame(info, fg_color='transparent')
            row.pack(fill='x', padx=18, pady=9)
            ctk.CTkLabel(row, text=label + ' :', width=95, anchor='w',
                         font=('Segoe UI', 12), text_color='#AAAAAA').pack(side='left')
            ctk.CTkLabel(row, text=str(value), anchor='w', font=('Segoe UI', 12, 'bold'),
                         text_color='#00FF66' if label == 'Status' else '#FFFFFF').pack(side='left')
        ctk.CTkButton(dialog, text='← Kembali', command=close_profile,
                      width=140, fg_color='#991B1B', hover_color='#7f1d1d').pack(pady=(3, 15))

    def open_app_settings(self, parent):
        dialog = self._front_window(parent)
        dialog.title('JKSY • Setting')
        dialog.geometry('450x445')
        dialog.resizable(False, False)
        ctk.CTkLabel(dialog, text='System Setting', font=('Segoe UI', 18, 'bold'),
                     text_color='#00FF66').pack(pady=(18, 12))
        ctk.CTkLabel(dialog, text='API AI (opsional, untuk J Ai)', anchor='w').pack(fill='x', padx=25)
        api_provider = ctk.StringVar(value='J Ai')
        ctk.CTkOptionMenu(dialog, variable=api_provider, values=['J Ai', 'Open Ai'], width=390).pack(padx=25, pady=(2, 5))
        api = ctk.CTkEntry(dialog, width=390, placeholder_text='Masukkan API Key', show='•')
        api.pack(padx=25, pady=(4, 5))
        ctk.CTkLabel(dialog, text='Key hanya disimpan selama sesi aplikasi.',
                     font=('Segoe UI', 10), text_color='#999999').pack(anchor='w', padx=25, pady=(0, 12))
        ctk.CTkLabel(dialog, text='Grafik', anchor='w').pack(fill='x', padx=25)
        graphics = ctk.StringVar(value=self.preferences['graphics'])
        ctk.CTkOptionMenu(dialog, variable=graphics,
                          values=['Low', 'Medium', 'High', 'Ultra'], width=390).pack(pady=(4, 12))
        ctk.CTkLabel(dialog, text='FPS', anchor='w').pack(fill='x', padx=25)
        fps = ctk.StringVar(value=self.preferences['fps'])
        ctk.CTkOptionMenu(dialog, variable=fps,
                          values=['30', '60', '90', '120'], width=390).pack(pady=(4, 12))
        def save():
            self.preferences = {'graphics': graphics.get(), 'fps': fps.get()}
            key = api.get().strip()
            if key:
                # Dipakai sebagai API manual J Ai dalam proses yang sama; tidak ditulis ke JSON.
                env_name = 'GEMINI_API_KEY' if api_provider.get() == 'J Ai' else 'OPENAI_API_KEY'
                os.environ[env_name] = key
            try:
                self.save_user_settings()
            except OSError as exc:
                messagebox.showerror('Setting', str(exc), parent=dialog)
                return
            messagebox.showinfo('Setting',
                'Preferensi berhasil disimpan. Grafik/FPS adalah preferensi tampilan; '
                'belum mengubah performa pemindaian. API Key (jika ada) aktif selama sesi.',
                parent=dialog)
            dialog.destroy()
        ctk.CTkButton(dialog, text='Save', command=save, width=150,
                      fg_color=UNLOCK_COLOR).pack(pady=8)

    def open_unlock_setup(self, parent):
        if self.login_mode == 'trial':
            messagebox.showwarning('Trial Mode', 'Unlock Tools hanya untuk akun Premium.', parent=parent)
            return
        auth = self._front_window(parent)
        auth.title('JKSY • Unlock Auth Key')
        auth.geometry('420x245')
        auth.resizable(False, False)
        ctk.CTkLabel(auth, text='🔒 Unlock Tools', font=('Segoe UI', 18, 'bold'),
                     text_color='#FFCC66').pack(pady=(20, 9))
        ctk.CTkLabel(auth, text='Verifikasi Auth Key sebelum memilih tools.').pack()
        entry = ctk.CTkEntry(auth, show='*', placeholder_text='Input Auth Key', width=325)
        entry.pack(pady=(12, 8))
        feedback = ctk.CTkLabel(auth, text='', text_color='#FF5555')
        feedback.pack()
        def verify():
            if not validate_jksy_auth(entry.get()):
                feedback.configure(text='Auth Key salah.')
                entry.delete(0, 'end')
                return
            auth.destroy()
            self.open_unlock_picker(parent)
        ctk.CTkButton(auth, text='Verify Key', command=verify, fg_color=UNLOCK_COLOR,
                      width=140).pack(pady=8)
        entry.bind('<Return>', lambda event: verify())
        entry.focus_set()

    def open_unlock_picker(self, parent):
        if self.login_mode == 'trial':
            messagebox.showwarning('Trial Mode', 'Unlock Tools hanya untuk akun Premium.', parent=parent)
            return
        dialog = self._front_window(parent)
        dialog.title('JKSY • Unlock Tools')
        dialog.geometry('455x485')
        dialog.resizable(False, False)
        ctk.CTkLabel(dialog, text='Pilih Tools', font=('Segoe UI', 18, 'bold'),
                     text_color='#00FF66').pack(pady=(15, 4))
        ctk.CTkLabel(dialog, text='Hijau = UNLOCK • Merah = LOCK',
                     text_color='#AAAAAA').pack(pady=(0, 9))

        # Area list dapat di-scroll tanpa menggeser judul dan tombol Done.
        action_bar = ctk.CTkFrame(dialog, fg_color='transparent')
        action_bar.pack(side='bottom', fill='x', pady=(9, 13))
        ctk.CTkButton(action_bar, text='Done', command=dialog.destroy, width=120,
                      fg_color=UNLOCK_COLOR).pack()

        scroll_area = ctk.CTkScrollableFrame(
            dialog, fg_color='transparent', corner_radius=0,
            scrollbar_button_color='#1f538d',
            scrollbar_button_hover_color='#2b8a3e',
        )
        scroll_area.pack(fill='both', expand=True, padx=(19, 13), pady=(2, 0))
        btns = {}
        for tool in READY_TOOLS:
            row = ctk.CTkFrame(scroll_area, fg_color='#191919', corner_radius=7)
            row.pack(fill='x', padx=(4, 6), pady=3)
            ctk.CTkLabel(row, text=tool, width=165, anchor='w').pack(side='left', padx=10, pady=8)

            def toggle(name=tool):
                if name in self.unlocked_tools:
                    self.unlocked_tools.remove(name)
                else:
                    self.unlocked_tools.add(name)
                btns[name].configure(
                    text='UNLOCK' if name in self.unlocked_tools else 'LOCK',
                    fg_color=UNLOCK_COLOR if name in self.unlocked_tools else LOCK_COLOR,
                    hover_color='#216e31' if name in self.unlocked_tools else '#7f1d1d',
                )
                self.update_tool_buttons()

            btns[tool] = ctk.CTkButton(
                row, text='UNLOCK' if tool in self.unlocked_tools else 'LOCK',
                fg_color=UNLOCK_COLOR if tool in self.unlocked_tools else LOCK_COLOR,
                hover_color='#216e31' if tool in self.unlocked_tools else '#7f1d1d',
                command=toggle, width=115,
            )
            btns[tool].pack(side='right', padx=8)

    def update_tool_buttons(self):
        for tool, btn in self.tool_buttons.items():
            try:
                unlocked = tool in self.unlocked_tools
                btn.configure(fg_color=UNLOCK_COLOR if unlocked else LOCK_COLOR,
                              hover_color='#216e31' if unlocked else '#7f1d1d')
            except Exception:
                pass

    def fetch_network_geo_info(self):
        try:
            req = urllib.request.Request("http://ip-api.com/json/", headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                country = data.get("country", "Unknown")
                city = data.get("city", "Unknown")
                ip = data.get("query", "127.0.0.1")
                self.geo_info = f"{country} : {city}"
                self.public_ip = ip
        except Exception:
            self.geo_info = "Indonesia : Local"
            try:
                self.public_ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                self.public_ip = "127.0.0.1"

    def init_trial_system(self):
        current_time = time.time()
        if os.path.exists(LICENSE_FILE):
            try:
                with open(LICENSE_FILE, "r") as f:
                    expiry_time = float(f.read().strip())
                self.expiry_time = expiry_time
            except Exception:
                self.expiry_time = current_time + TRIAL_DURATION
                with open(LICENSE_FILE, "w") as f:
                    f.write(str(self.expiry_time))
        else:
            self.expiry_time = current_time + TRIAL_DURATION
            with open(LICENSE_FILE, "w") as f:
                f.write(str(self.expiry_time))

    def clear_window(self):
        self.clock_running = False
        for widget in self.winfo_children():
            widget.destroy()

    def _reset_login_session(self):
        if self.trial_after_id is not None:
            try:
                self.after_cancel(self.trial_after_id)
            except Exception:
                pass
            self.trial_after_id = None
        self.unlocked_tools.clear()
        self.login_mode = None

    def build_login_frame(self):
        self._reset_login_session()
        self.clear_window()
        self.geometry('425x450')
        self.is_premium = False
        outer = ctk.CTkFrame(self, fg_color='#181818', corner_radius=14)
        outer.place(relx=.5, rely=.5, anchor='center')
        ctk.CTkLabel(outer, text='◆ JKSY TOOLS KIT', font=('Segoe UI', 23, 'bold'),
                     text_color='#00FF66').pack(padx=35, pady=(26, 4))
        ctk.CTkLabel(outer, text='Secure Member Access', text_color='#aab0b8',
                     font=('Segoe UI', 12)).pack(pady=(0, 19))
        self.user_entry = ctk.CTkEntry(outer, placeholder_text='User', width=330, height=39)
        self.user_entry.pack(pady=5)
        self.pass_entry = ctk.CTkEntry(outer, placeholder_text='Password', show='●', width=330, height=39)
        self.pass_entry.pack(pady=5)
        self.pass_entry.bind('<Return>', lambda _event: self.verify_key())
        self.error_label = ctk.CTkLabel(outer, text='', text_color='#FF5555',
                                        font=('Segoe UI', 11), wraplength=315)
        self.error_label.pack(pady=(3, 1))
        row = ctk.CTkFrame(outer, fg_color='transparent')
        row.pack(padx=30, pady=(4, 9))
        ctk.CTkButton(row, text='Login', width=157, fg_color='#2b8a3e',
                      command=self.verify_key).pack(side='left', padx=(0, 8))
        ctk.CTkButton(row, text='Register', width=157, fg_color='#1f538d',
                      command=self.open_register).pack(side='left')
        remaining = max(0, int(self.expiry_time - time.time()))
        trial_label = 'Trial • 5 Menit (J Ai Only)' if remaining else 'Trial • Expired'
        ctk.CTkButton(outer, text=trial_label, width=330,
                      state='normal' if remaining else 'disabled',
                      fg_color='#a86b19', command=self.enter_trial_mode).pack(pady=(3, 9))
        ctk.CTkButton(outer, text='Authkey', width=330, height=34,
                      fg_color='#1f538d', hover_color='#143c68',
                      command=self.open_authkey_login).pack(pady=(0, 10))
        ctk.CTkLabel(outer, text='Trial hanya mengizinkan J Ai selama waktu tersedia.',
                     font=('Segoe UI', 10), text_color='#9199a5').pack(pady=(0, 23))
        self.user_entry.focus_set()

    def open_authkey_login(self):
        """Masuk Premium dengan System Key legacy, tanpa memerlukan username."""
        dialog = self._front_window(self)
        dialog.title('JKSY • Authkey Access')
        dialog.geometry('390x250')
        dialog.resizable(False, False)
        dialog.configure(fg_color='#121212')
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text='🔑 AUTHKEY ACCESS', font=('Segoe UI', 17, 'bold'),
                     text_color='#00FF66').pack(pady=(19, 8))
        ctk.CTkLabel(dialog, text='Masukkan System Key untuk masuk Premium.',
                     font=('Segoe UI', 11), text_color='#aab0b8').pack(pady=(0, 10))
        key_entry = ctk.CTkEntry(dialog, placeholder_text='Input System Key',
                                 show='●', width=300, height=36)
        key_entry.pack(pady=(0, 6))
        feedback = ctk.CTkLabel(dialog, text='', text_color='#FF5555',
                                font=('Segoe UI', 11))
        feedback.pack(pady=(0, 4))

        def unlock():
            value = key_entry.get()
            if hmac.compare_digest(hashlib.md5(value.encode()).hexdigest(), internal_stk):
                dialog.grab_release()
                dialog.destroy()
                self._reset_login_session()
                self.login_mode = 'premium'
                self.is_premium = True
                self.build_dashboard_menu()
            else:
                feedback.configure(text='Authkey salah. Akses ditolak.')
                key_entry.delete(0, 'end')

        key_entry.bind('<Return>', lambda _event: unlock())
        actions = ctk.CTkFrame(dialog, fg_color='transparent')
        actions.pack(pady=(1, 12))
        ctk.CTkButton(actions, text='Unlock', width=140,
                      fg_color='#2b8a3e', command=unlock).pack(side='left', padx=5)
        ctk.CTkButton(actions, text='Cancel', width=140,
                      fg_color='#991B1B', command=dialog.destroy).pack(side='left', padx=5)
        dialog.after(100, key_entry.focus_set)

    def open_register(self):
        dialog = self._front_window(self)
        dialog.title('JKSY • Register')
        dialog.geometry('445x560')
        dialog.resizable(False, False)
        dialog.configure(fg_color='#121212')
        dialog.transient(self)
        ctk.CTkLabel(dialog, text='REGISTER ACCOUNT', font=('Segoe UI', 19, 'bold'),
                     text_color='#00FF66').pack(pady=(18, 12))
        fields = {}
        for name, hint in [('User','Input Username'), ('E-mail','Input E-mail'),
                           ('IP','Input IP'), ('Password','Input Password'),
                           ('Ulangi Password','Ulangi Password')]:
            ctk.CTkLabel(dialog, text=name, anchor='w', text_color='#bec7d1').pack(fill='x', padx=42)
            is_secret = 'Password' in name
            entry = ctk.CTkEntry(dialog, placeholder_text=hint, height=32,
                                 show='●' if is_secret else '')
            entry.pack(fill='x', padx=42, pady=(2, 6))
            fields[name] = entry
        show = ctk.BooleanVar(value=False)
        def toggle():
            for field in ('Password','Ulangi Password'):
                fields[field].configure(show='' if show.get() else '●')
        ctk.CTkCheckBox(dialog, text='Lihat Password', variable=show, command=toggle,
                        font=('Segoe UI', 11)).pack(anchor='w', padx=42, pady=(0, 10))
        ctk.CTkButton(dialog, text='Send Register', fg_color='#2b8a3e',
                      command=lambda: messagebox.showinfo('Register Full',
                          'Antrian Full / Hubungi Developer Kami', parent=dialog)).pack(pady=(0, 12))
        actions = ctk.CTkFrame(dialog, fg_color='transparent')
        actions.pack(pady=(0, 15))
        ctk.CTkButton(actions, text='Exit', width=125, fg_color='#991B1B',
                      command=dialog.destroy).pack(side='left', padx=5)
        ctk.CTkButton(actions, text='Admin', width=125, fg_color='#1f538d',
                      command=self.open_telegram_pro).pack(side='left', padx=5)

    def verify_key(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()
        if not username:
            self.error_label.configure(text='Masukkan User terlebih dahulu.')
            return
        # Legacy password digest is retained for compatibility; username is not a verified account.
        if hmac.compare_digest(hashlib.md5(password.encode()).hexdigest(), internal_stk):
            self._reset_login_session()
            self.login_mode = 'premium'
            self.is_premium = True
            self.build_dashboard_menu()
        else:
            self.error_label.configure(text='User atau Password tidak valid.')

    def _check_trial_expiry(self):
        self.trial_after_id = None
        if self.login_mode != 'trial':
            return
        if time.time() >= self.expiry_time:
            # Close child windows to avoid continuing to use J Ai after expiry.
            for child in list(self.winfo_children()):
                if isinstance(child, ctk.CTkToplevel):
                    try:
                        child.destroy()
                    except Exception:
                        pass
            self.deiconify()
            self.build_login_frame()
            messagebox.showinfo('Trial Expired', 'Trial 5 menit telah habis.', parent=self)
            return
        self.trial_after_id = self.after(500, self._check_trial_expiry)

    def enter_trial_mode(self):
        if time.time() >= self.expiry_time:
            self.error_label.configure(text='Durasi Trial sudah habis.')
            return
        self._reset_login_session()
        self.login_mode = 'trial'
        self.is_premium = False
        self.unlocked_tools.add('J Ai')
        self.build_dashboard_menu()
        self._check_trial_expiry()

    def open_telegram_pro(self):
        webbrowser.open("https://t.me/nazisme1930")

    def show_under_maintenance_popup(self, feature_name):
        m_dialog = self._front_window(self)
        m_dialog.title("Under Maintenance")
        m_dialog.geometry("340x220")
        m_dialog.resizable(False, False)

        lbl_title = ctk.CTkLabel(m_dialog, text=f"⚠️ {feature_name} Feature", font=("Segoe UI", 14, "bold"), text_color="#FFA500")
        lbl_title.pack(pady=(18, 4))

        lbl_sub = ctk.CTkLabel(m_dialog, text="Under Maintenance", font=("Segoe UI", 16, "bold"), text_color="#FF5555")
        lbl_sub.pack(pady=(0, 10))

        gear_label = ctk.CTkLabel(m_dialog, text="⚙️", font=("Segoe UI", 36))
        gear_label.pack(pady=(0, 10))

        def rotate_gear(idx=0):
            if m_dialog.winfo_exists():
                gear_label.configure(text=["⚙️", "🔄", "⏳"][idx % 3])
                m_dialog.after(500, lambda: rotate_gear(idx + 1))

        rotate_gear()

        def close_dialog():
            m_dialog.destroy()

        m_dialog.protocol("WM_DELETE_WINDOW", close_dialog)

        btn_ok = ctk.CTkButton(
            m_dialog, text="OK", command=close_dialog, 
            width=100, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), 
            fg_color="#1f538d", hover_color="#143c68", text_color="white"
        )
        btn_ok.pack(pady=(0, 10))

    def require_tool_auth(self, tool_name, launch_callback):
        """Jalankan tools terpilih bila sudah unlock, atau minta Auth Key."""
        if self.login_mode == 'trial':
            if time.time() >= self.expiry_time or tool_name != 'J Ai':
                messagebox.showwarning('Trial Mode', 'Trial hanya menyediakan akses J Ai.', parent=self)
                return
        if tool_name in self.unlocked_tools:
            launch_callback()
            return
        dialog = self._front_window(self)
        dialog.title(f"JKSY Authorization - {tool_name}")
        dialog.geometry("390x235")
        dialog.resizable(False, False)
        dialog.transient(self)

        ctk.CTkLabel(dialog, text=f"🔒 {tool_name} - Locked", font=("Segoe UI", 16, "bold"),
                     text_color="#FFCC66").pack(pady=(20, 7))
        ctk.CTkLabel(dialog, text="Masukkan Auth Key untuk membuka modul ini.",
                     font=("Segoe UI", 11), text_color="#AAAAAA").pack(pady=(0, 10))
        entry = ctk.CTkEntry(dialog, placeholder_text="Input Auth Key", show="*",
                             width=300, height=35, font=("Segoe UI", 12))
        entry.pack(pady=(0, 5))
        feedback = ctk.CTkLabel(dialog, text="", text_color="#FF5555", font=("Segoe UI", 11))
        feedback.pack(pady=(0, 5))

        def submit_key():
            candidate = entry.get()
            if not validate_jksy_auth(candidate):
                feedback.configure(text="❌ Auth Key salah. Akses ditolak.")
                entry.delete(0, "end")
                return
            dialog.destroy()
            self.unlocked_tools.add(tool_name)
            self.update_tool_buttons()
            launch_callback()

        ctk.CTkButton(dialog, text="Unlock", command=submit_key, width=150,
                      fg_color="#2b8a3e", hover_color="#216e31").pack(pady=(4, 0))
        entry.bind("<Return>", lambda _event: submit_key())
        dialog.after(100, lambda: entry.focus_set() if dialog.winfo_exists() else None)

    def open_premium_tab(self):
        # Premium Control Center dibuka berdampingan dengan dashboard.

        prem_window = self._front_window(self)
        prem_window.title("JKSY Tools Kit - Premium Terminal & Status")
        prem_window.geometry("860x580")
        prem_window.resizable(False, False)

        def close_premium_window():
            prem_window.destroy()

        prem_window.protocol("WM_DELETE_WINDOW", close_premium_window)

        lbl_title = ctk.CTkLabel(prem_window, text="⭐ JKSY Premium Control Center & Terminal", font=("Segoe UI", 18, "bold"), text_color="#00FF66")
        lbl_title.pack(pady=(12, 2))

        lbl_sub = ctk.CTkLabel(prem_window, text="Status akses tools dan terminal eksklusif untuk user premium.", font=("Segoe UI", 12), text_color="gray")
        lbl_sub.pack(pady=(0, 8))

        container = ctk.CTkFrame(prem_window, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        left_frame = ctk.CTkFrame(container, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        lbl_box_title = ctk.CTkLabel(left_frame, text="📊 Tools Premium Status", font=("Segoe UI", 12, "bold"), text_color="#00FFFF")
        lbl_box_title.pack(anchor="w", padx=2, pady=(0, 4))

        status_textbox = ctk.CTkTextbox(left_frame, width=390, height=410, font=("Consolas", 11), fg_color="#000000", text_color="#00FF66", wrap="none")
        status_textbox.pack(fill="both", expand=True)

        access_type = "UNLIMITED PREMIUM" if self.is_premium else "TRIAL 5 MINUTES ACTIVE"
        status_lines = [
            '=== JKSY TOOLS KIT STATUS ===',
            f'AUTH LEVEL : {access_type}',
            '-----------------------------------------',
        ]
        for tool in READY_TOOLS:
            if tool in self.unlocked_tools:
                status_lines.append(f'[✔] {tool:<11} : UNLOCK')
            else:
                status_lines.append(f'[🔒] {tool:<11} : AUTH KEY REQUIRED')
        for tool in ('Mods', 'Crack', 'Spam', 'Wa API',
                     'Tracking', 'Host Ai', 'Picture', 'Drop Box', 'Nawala', 'Analys'):
            status_lines.append(f'[🔒] {tool:<11} : UNDER MAINTENANCE')
        status_lines += ['-----------------------------------------', 'Status Sistem: STABLE & SECURE']
        tools_status_content = '\n'.join(status_lines) + '\n'
        status_textbox.insert("0.0", tools_status_content)
        status_textbox.configure(state="disabled")

        right_frame = ctk.CTkFrame(container, fg_color="transparent")
        right_frame.pack(side="right", fill="both", expand=True, padx=(8, 0))

        lbl_term_title = ctk.CTkLabel(right_frame, text="💻 Premium Terminal (PowerShell)", font=("Segoe UI", 12, "bold"), text_color="#FFD700")
        lbl_term_title.pack(anchor="w", padx=2, pady=(0, 4))

        term_textbox = ctk.CTkTextbox(right_frame, width=390, height=360, font=("Consolas", 11), fg_color="#000000", text_color="#00FFFF", wrap="none")
        term_textbox.pack(fill="both", expand=True, pady=(0, 6))
        term_textbox.insert("0.0", "JKSY Premium Shell v6.9.12 ready.\nKetik perintah sistem di bawah lalu tekan Enter atau klik Run.\n\n")
        term_textbox.configure(state="disabled")

        def run_terminal_cmd(cmd_str):
            if not cmd_str.strip():
                return
            term_textbox.configure(state="normal")
            term_textbox.insert("end", f"\nPS > {cmd_str}\n")
            term_textbox.configure(state="disabled")

            def worker():
                try:
                    import subprocess as sub_proc
                    formatted_cmd = "Get-ChildItem | Select-Object Mode, LastWriteTime, Length, Name | Format-Table -AutoSize" if cmd_str.strip().lower() in ["ls", "dir"] else cmd_str
                    process = sub_proc.Popen(["powershell", "-Command", formatted_cmd], stdout=sub_proc.PIPE, stderr=sub_proc.PIPE, text=True)
                    stdout, stderr = process.communicate()
                    output = stdout if stdout else stderr
                    
                    cleaned_lines = [line.rstrip() for line in output.splitlines() if line.strip() != ""]
                    res = "\n".join(cleaned_lines) if cleaned_lines else "Perintah dieksekusi tanpa output."
                except Exception as e:
                    res = f"Error: {e}"

                term_textbox.configure(state="normal")
                term_textbox.insert("end", res + "\n\n" + "="*45 + "\n")
                term_textbox.see("end")
                term_textbox.configure(state="disabled")

            threading.Thread(target=worker, daemon=True).start()

        term_input_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        term_input_frame.pack(fill="x")

        term_entry = ctk.CTkEntry(term_input_frame, placeholder_text="Ketik perintah ...", height=BTN_HEIGHT, font=("Consolas", 11))
        term_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        term_entry.bind("<Return>", lambda event: [run_terminal_cmd(term_entry.get()), term_entry.delete(0, "end")])

        btn_run = ctk.CTkButton(
            term_input_frame, text="Run", command=lambda: [run_terminal_cmd(term_entry.get()), term_entry.delete(0, "end")],
            width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 11, "bold"), fg_color="#1f538d", hover_color="#143c68", text_color="white"
        )
        btn_run.pack(side="right")

        bottom_frame = ctk.CTkFrame(prem_window, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=20, pady=(0, 15))

        btn_exit = ctk.CTkButton(
            bottom_frame, text="❌ Exit / Kembali", command=close_premium_window,
            width=160, height=32, font=("Segoe UI", 12, "bold"),
            fg_color="#c92a2a", hover_color="#a61e1e", text_color="white"
        )
        btn_exit.pack(side="right")

    def build_dashboard_menu(self):
        self.tool_buttons = {}
        self.clear_window()
        self.geometry("780x560")

        lbl_title = ctk.CTkLabel(self, text="⚡ JKSY Tools Kit version 6.9.12", font=("Segoe UI", 18, "bold"))
        lbl_title.pack(pady=(12, 2))

        lbl_sub = ctk.CTkLabel(self, text="Pilih modul tools yang ingin digunakan:", font=("Segoe UI", 12), text_color="gray")
        lbl_sub.pack(pady=(0, 8))

        main_layout_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_layout_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        col_left = ctk.CTkFrame(main_layout_frame, fg_color="transparent")
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        box_left = ctk.CTkFrame(col_left, fg_color=("#e9ecef", "#111111"), corner_radius=10, border_width=1, border_color="#333333")
        box_left.pack(fill="x", pady=(0, 6))

        lbl_head_left = ctk.CTkLabel(box_left, text="💻 Device & Hardware Info", font=("Segoe UI", 12, "bold"), text_color=("#1f538d", "#00FFFF"))
        lbl_head_left.pack(anchor="w", padx=12, pady=(8, 4))

        self.box_hw_text = ctk.CTkTextbox(box_left, height=170, font=("Consolas", 11), fg_color="#000000", text_color="#00FF66")
        self.box_hw_text.pack(fill="x", expand=True, padx=10, pady=(0, 8))

        tk_panel = ctk.CTkFrame(col_left, fg_color="transparent")
        tk_panel.pack(fill="x", pady=(2, 0))

        lbl_tk = ctk.CTkLabel(tk_panel, text="🚀 Tools Modul:", font=("Segoe UI", 11, "bold"), text_color="gray", anchor="w")
        lbl_tk.pack(anchor="w", padx=2, pady=(0, 2))

        tk_grid = ctk.CTkFrame(tk_panel, fg_color="transparent")
        tk_grid.pack(fill="x")

        # Modul aktif hijau; fitur yang belum tersedia membuka popup Under Maintenance
        takeover_buttons = [
            ("Takeover", lambda: self.require_tool_auth("Takeover", self.open_jksy_takeover), LOCK_COLOR, "#7f1d1d", "white"),
            ("Finder", lambda: self.require_tool_auth("Finder", self.open_jksy_finder), LOCK_COLOR, "#7f1d1d", "white"),
            ("Scanner", lambda: self.require_tool_auth("Scanner", self.open_jksy_scanner), LOCK_COLOR, "#7f1d1d", "white"),
            ("Brute Force", lambda: self.require_tool_auth("Brute Force", self.open_jksy_bruteforce), LOCK_COLOR, "#7f1d1d", "white"),
            ("Web Shell", lambda: self.require_tool_auth("Web Shell", self.open_jksy_webshell), LOCK_COLOR, "#7f1d1d", "white"),
            ("Ddos", lambda: self.require_tool_auth("Ddos", self.open_jksy_ddos), LOCK_COLOR, "#7f1d1d", "white"),
            ("Traffic", lambda: self.require_tool_auth("Traffic", self.open_jksy_traffic), LOCK_COLOR, "#7f1d1d", "white"),
            ("Mods", lambda: self.show_under_maintenance_popup("Mods"), "#1f538d", "#143c68", "white"),
            ("Crack", lambda: self.show_under_maintenance_popup("Crack"), "#1f538d", "#143c68", "white"),
            ("Spam", lambda: self.show_under_maintenance_popup("Spam"), "#1f538d", "#143c68", "white"),
            ("Wa API", lambda: self.show_under_maintenance_popup("Wa API"), "#1f538d", "#143c68", "white"),
            ("Tracking", lambda: self.show_under_maintenance_popup("Tracking"), "#1f538d", "#143c68", "white"),
            ("Host Ai", lambda: self.show_under_maintenance_popup("Host Ai"), "#1f538d", "#143c68", "white"),
            ("Picture", lambda: self.show_under_maintenance_popup("Picture"), "#1f538d", "#143c68", "white"),
            ("Drop Box", lambda: self.show_under_maintenance_popup("Drop Box"), "#1f538d", "#143c68", "white"),
            ("J Ai", lambda: self.require_tool_auth("J Ai", self.open_jksy_ai), LOCK_COLOR, "#7f1d1d", "white"),
            ("Nawala", lambda: self.show_under_maintenance_popup("Nawala"), "#1f538d", "#143c68", "white"),
            ("Authority", lambda: self.require_tool_auth("Authority", self.open_jksy_authority), LOCK_COLOR, "#7f1d1d", "white"),
            ("Analys", lambda: self.show_under_maintenance_popup("Analys"), "#1f538d", "#143c68", "white")
        ]

        for idx, (txt, cmd, bg, hov, fg) in enumerate(takeover_buttons):
            r = idx // 4
            c = idx % 4
            b = ctk.CTkButton(tk_grid, text=txt, command=cmd, width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 10, "bold"), fg_color=bg, hover_color=hov, text_color=fg)
            b.grid(row=r, column=c, padx=3, pady=3, sticky="ew")
            if txt in READY_TOOLS:
                self.tool_buttons[txt] = b

        self.update_tool_buttons()
        for c_idx in range(4):
            tk_grid.columnconfigure(c_idx, weight=1)

        col_right = ctk.CTkFrame(main_layout_frame, fg_color="transparent")
        col_right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        box_right = ctk.CTkFrame(col_right, fg_color=("#e9ecef", "#111111"), corner_radius=10, border_width=1, border_color="#333333")
        box_right.pack(fill="x", pady=(0, 6))

        lbl_head_right = ctk.CTkLabel(box_right, text="🌐 Network & Session Info", font=("Segoe UI", 12, "bold"), text_color=("#2b8a3e", "#00FF66"))
        lbl_head_right.pack(anchor="w", padx=12, pady=(8, 4))

        self.box_geo_text = ctk.CTkTextbox(box_right, height=170, font=("Consolas", 11), fg_color="#000000", text_color="#00FFFF")
        self.box_geo_text.pack(fill="x", expand=True, padx=10, pady=(0, 8))

        lg_panel = ctk.CTkFrame(col_right, fg_color="transparent")
        lg_panel.pack(fill="x", pady=(2, 0))

        lbl_lg = ctk.CTkLabel(lg_panel, text="⚙️ System & Account:", font=("Segoe UI", 11, "bold"), text_color="gray", anchor="w")
        lbl_lg.pack(anchor="w", padx=2, pady=(0, 2))

        lg_grid = ctk.CTkFrame(lg_panel, fg_color="transparent")
        lg_grid.pack(fill="x")

        account_buttons = [
            ("Profile", self.show_profile, "#2b8a3e", "#216e31", "white", 0, None),
            ("Setup", self.show_setup, "#2b8a3e", "#216e31", "white", 0, None),
            ("Premium", self.open_premium_tab, "#2b8a3e", "#216e31", "white", 0, None), 
            ("Logout", self.build_login_frame, "#2b8a3e", "#216e31", "white", 0, None)
        ]

        for idx, (txt, cmd, bg, hov, fg, b_w, b_c) in enumerate(account_buttons):
            r = idx // 4
            c = idx % 4
            b = ctk.CTkButton(lg_grid, text=txt, command=cmd, width=BTN_WIDTH, height=BTN_HEIGHT, font=("Segoe UI", 10, "bold"), fg_color=bg, hover_color=hov, text_color=fg, border_width=b_w, border_color=b_c)
            b.grid(row=r, column=c, padx=3, pady=3, sticky="ew")

        for c_idx in range(4):
            lg_grid.columnconfigure(c_idx, weight=1)

        self.clock_running = True
        threading.Thread(target=self.update_dashboard_realtime, daemon=True).start()

    def update_dashboard_realtime(self):
        os_info = f"{platform.system()} {platform.release()}"
        device_info = platform.machine() or "x86_64"
        try:
            user_name = os.getlogin()
        except Exception:
            user_name = socket.gethostname()

        if psutil:
            ram_total = round(psutil.virtual_memory().total / (1024.0 ** 3), 1)
            ram_str = f"{ram_total} GB"
            disk_usage = shutil.disk_usage("C:" if os.name == 'nt' else "/")
            ssd_total = round(disk_usage.total / (1024.0 ** 3), 1)
            ssd_str = f"{ssd_total} GB"
        else:
            ram_str = "8.0 GB"
            ssd_str = "256.0 GB"

        hw_formatted = (
            f"OS     : {os_info}\n"
            f"Device : {device_info}\n"
            f"User   : {user_name}\n"
            f"SSD    : {ssd_str}\n"
            f"RAM    : {ram_str}\n\n"
            f"Status Hardware: NORMAL"
        )

        self.box_hw_text.configure(state="normal")
        self.box_hw_text.delete("0.0", "end")
        self.box_hw_text.insert("0.0", hw_formatted)
        self.box_hw_text.configure(state="disabled")

        while self.clock_running:
            try:
                now = datetime.datetime.now()
                day_num = now.day
                month_str = MONTH_NAMES_ID.get(now.month, str(now.month))
                year_num = now.year
                date_formatted = f"{day_num} {month_str} {year_num}"

                time_formatted = now.strftime("%H:%M:%S WIB")
                status_str = "Premium Access" if self.is_premium else "Trial Access (5 Mins)"

                geo_formatted = (
                    f"Date   : {date_formatted}\n"
                    f"Time   : {time_formatted}\n"
                    f"Geo    : {self.geo_info}\n"
                    f"IPv    : {self.public_ip}\n"
                    f"Status : {status_str}\n\n"
                    f"Session Access: VERIFIED"
                )

                self.box_geo_text.configure(state="normal")
                self.box_geo_text.delete("0.0", "end")
                self.box_geo_text.insert("0.0", geo_formatted)
                self.box_geo_text.configure(state="disabled")
            except Exception:
                pass
            time.sleep(1)

    def open_jksy_traffic(self):
        """Open Traffic HTTP diagnostics without hiding the dashboard."""
        try:
            tf_jksy.open_window(self)
        except Exception as exc:
            messagebox.showerror('Traffic', f'Gagal membuka modul: {exc}', parent=self)

    def open_jksy_authority(self):
        """Open Ahrefs domain/URL analysis as a separate window."""
        try:
            au_jksy.open_window(self)
        except Exception as exc:
            messagebox.showerror('Authority', f'Gagal membuka modul: {exc}', parent=self)

    def open_jksy_webshell(self):
        """Directory audit for one explicitly configured authorized HTTPS target."""
        from tkinter import messagebox
        try:
            ws_jksy.open_window(self)
        except Exception as exc:
            messagebox.showerror('Web Shell', f'Gagal membuka modul: {exc}', parent=self)

    def open_jksy_ai(self):
        """J Ai dipanggil setelah Auth Key launcher berhasil diverifikasi."""
        from tkinter import messagebox
        try:
            j_ai.open_window(self)
        except Exception as exc:
            messagebox.showerror("J Ai", f"Gagal membuka modul: {exc}", parent=self)

    def open_jksy_bruteforce(self):
        """Tampilkan Website Login Tester lalu kembali ke launcher saat ditutup."""
        from tkinter import messagebox
        try:
            bf_window = bf_jksy.open_window(self)
        except Exception as exc:
            messagebox.showerror("Brute Force", f"Gagal membuka modul: {exc}", parent=self)
            return

        def return_to_launcher():
            if bf_window.winfo_exists():
                bf_window.destroy()

        bf_window.protocol("WM_DELETE_WINDOW", return_to_launcher)

    def open_jksy_scanner(self):
        """Buka scanner terpisah dan kembali ke launcher saat scanner ditutup."""
        from tkinter import messagebox

        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, "toolskit", "sc-jksy.py"),
            os.path.join(base_dir, "sc-jksy.py"),
        ]
        scanner_path = next((p for p in candidates if os.path.isfile(p)), None)
        if scanner_path is None:
            messagebox.showerror(
                "Scanner tidak ditemukan",
                "File sc-jksy.py tidak ditemukan di folder toolskit atau folder aplikasi.py.",
                parent=self,
            )
            return

        try:
            scanner_env = os.environ.copy()
            scanner_env["JKSY_SCANNER_LAUNCH"] = "launcher-v1"
            scanner_env["JKSY_SCANNER_PARENT_PID"] = str(os.getpid())
            process = subprocess.Popen(
                [sys.executable, scanner_path],
                cwd=os.path.dirname(scanner_path),
                env=scanner_env,
            )
        except OSError as exc:
            messagebox.showerror("Gagal membuka Scanner", str(exc), parent=self)
            return

        # Scanner berjalan sebagai proses terpisah; dashboard tidak ditutup.

    def _open_legacy_window(self, filename, class_name, display_name):
        """Jalankan GUI CTk root lama sebagai proses mandiri agar dashboard tetap aktif.

        Pemanggilan lewat -c mengimpor modul tanpa menjalankan blok __main__.
        Auth Key tetap diverifikasi oleh require_tool_auth sebelum pemanggilan ini.
        """
        module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'toolskit', filename)
        if not os.path.isfile(module_path):
            messagebox.showerror(display_name, f'File modul tidak ditemukan: {module_path}', parent=self)
            return
        runner = (
            'import importlib.util, sys\n'
            'path, cls = sys.argv[1], sys.argv[2]\n'
            'spec = importlib.util.spec_from_file_location("jksy_child_tool", path)\n'
            'mod = importlib.util.module_from_spec(spec)\n'
            'spec.loader.exec_module(mod)\n'
            'app = getattr(mod, cls)(launcher_ref=None)\n'
            'app.mainloop()\n'
        )
        try:
            creationflags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0) if os.name == 'nt' else 0
            subprocess.Popen(
                [sys.executable, '-c', runner, module_path, class_name],
                cwd=os.path.dirname(module_path),
                creationflags=creationflags,
            )
        except (OSError, ValueError) as exc:
            messagebox.showerror(display_name, f'Gagal membuka modul: {exc}', parent=self)

    def open_jksy_takeover(self):
        self._open_legacy_window('tk-jksy.py', 'JKSYApp', 'Takeover')

    def open_jksy_ddos(self):
        self._open_legacy_window('d-jksy.py', 'DDoSApp', 'Ddos')

    def open_jksy_finder(self):
        """JKSY Finder menggunakan UI terpadu dari modul f-jksy.py."""
        finder_window = self._front_window(self)

        def close_finder_window():
            if finder_window.winfo_exists():
                finder_window.destroy()

        try:
            finder_jksy.render_jksy_finder(finder_window, on_back=close_finder_window)
        except Exception:
            close_finder_window()
            raise

    def render_finder_content(self, root):
        # Menyematkan logika UI dari f-jksy.py ke dalam jendela tab launcher
        frame_top = ctk.CTkFrame(root, fg_color="#0F172A")
        frame_top.pack(fill=ctk.X, padx=12, pady=12)
        
        lbl_tld = ctk.CTkLabel(frame_top, text="Masukkan Ekstensi TLD (misal: com, id, co.id):", font=("Segoe UI", 10, "bold"), text_color="#38BDF8")
        lbl_tld.pack(anchor="w", pady=(0, 8))
        
        frame_input_row = ctk.CTkFrame(frame_top, fg_color="transparent")
        frame_input_row.pack(fill=ctk.X)
        
        btn_width = 10
        btn_font = ("Segoe UI", 10, "bold")

        btn_save = ctk.CTkButton(frame_input_row, text="Save", fg_color="#1E3A8A", text_color="#93C5FD", font=btn_font, 
                                 hover_color="#2563EB", width=90, height=32, state="disabled", command=finder_jksy.save_results)
        btn_save.pack(side="right", padx=2)
        
        btn_clear = ctk.CTkButton(frame_input_row, text="Clear", fg_color="#7F1D1D", text_color="#FCA5A5", font=btn_font, 
                                  hover_color="#DC2626", width=90, height=32, 
                                  command=lambda: finder_jksy.clear_history(text_output, entry_tld, btn_search, btn_pause_resume, btn_save, lbl_domains_val, lbl_time_val, lbl_ms_val))
        btn_clear.pack(side="right", padx=(0, 10))
        
        btn_pause_resume = ctk.CTkButton(frame_input_row, text="Pause", fg_color="#334155", text_color="#94A3B8", font=btn_font, 
                                         hover_color="#475569", width=90, height=32, state="disabled", command=lambda: finder_jksy.toggle_pause_resume(btn_pause_resume))
        btn_pause_resume.pack(side="right", padx=(0, 10))
        
        btn_search = ctk.CTkButton(frame_input_row, text="Scan", fg_color="#10B981", text_color="white", font=btn_font, 
                                   hover_color="#059669", width=90, height=32, 
                                   command=lambda: finder_jksy.start_search(entry_tld, mode_var, tld_mode_var, text_output, btn_search, btn_pause_resume, btn_clear, btn_save, lbl_domains_val, lbl_time_val, lbl_ms_val))
        btn_search.pack(side="right", padx=(0, 10))
        
        mode_var = ctk.StringVar(root)
        mode_var.set("NONE")
        
        btn_mode = ctk.CTkButton(frame_input_row, textvariable=mode_var, fg_color="#1E293B", text_color="#38BDF8", font=btn_font,
                                 hover_color="#334155", width=90, height=32)
        btn_mode.pack(side="right", padx=(0, 10))
        
        # Menu popup untuk Mode Scanner
        menu_mode = ctk.CTkOptionMenu(frame_input_row, variable=mode_var, values=["NONE", "AUTO", "CRT.SH"], fg_color="#1E293B", button_color="#1E293B", width=90)
        # Mengganti tombol dengan option menu customtkinter agar lebih terintegrasi rapi
        btn_mode.pack_forget()
        menu_mode.pack(side="right", padx=(0, 10))

        tld_mode_var = ctk.StringVar(root)
        tld_mode_var.set("NONE")
        menu_tld = ctk.CTkOptionMenu(frame_input_row, variable=tld_mode_var, values=["NONE", "Manual", "Random"], fg_color="#1E293B", button_color="#1E293B", width=90)
        menu_tld.pack(side="right", padx=(0, 10))
        
        entry_tld = ctk.CTkEntry(frame_input_row, width=140, font=("Segoe UI", 12), fg_color="#1E293B", text_color="#F8FAFC")
        entry_tld.pack(side="left", padx=2)
        
        frame_bottom = ctk.CTkFrame(root, fg_color="#090D16")
        frame_bottom.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        frame_bottom.columnconfigure(0, weight=3)
        frame_bottom.columnconfigure(1, weight=2)
        frame_bottom.rowconfigure(0, weight=1)
        
        frame_left = ctk.CTkFrame(frame_bottom, fg_color="#0F172A")
        frame_left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        
        lbl_box1 = ctk.CTkLabel(frame_left, text="📊 Live Domain Log", font=("Segoe UI", 9, "bold"), text_color="#38BDF8")
        lbl_box1.pack(anchor="w", padx=12, pady=(12, 8))
        
        text_output = ctk.CTkTextbox(frame_left, wrap="word", font=("Consolas", 9), fg_color="#090D16", text_color="#34D399")
        text_output.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        text_output.configure(state="disabled")
        
        frame_right = ctk.CTkFrame(frame_bottom, fg_color="#0F172A")
        frame_right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        
        lbl_box2 = ctk.CTkLabel(frame_right, text="💻 System & Stats Dashboard", font=("Segoe UI", 9, "bold"), text_color="#38BDF8")
        lbl_box2.pack(anchor="w", padx=12, pady=(12, 10))
        
        os_info, cpu_info, ram_info = finder_jksy.get_system_info()
        
        info_items = [
            ("GET DOMAIN", "0"),
            ("TIME", "00:00"),
            ("OS", os_info),
            ("CPU", cpu_info),
            ("RAM", ram_info),
            ("MS", "0 ms"),
            ("Developer", "JOKESKYLS"),
            ("Telegram", "@nazisme1930")
        ]
        
        for label, val in info_items:
            row_f = ctk.CTkFrame(frame_right, fg_color="#1E293B")
            row_f.pack(fill="x", padx=12, pady=3)
            
            lbl_key = ctk.CTkLabel(row_f, text=label, font=("Segoe UI", 8, "bold"), text_color="#94A3B8", width=11, anchor="w")
            lbl_key.pack(side="left", padx=8, pady=6)
            
            val_fg = "#34D399" if label not in ["Developer", "Telegram"] else "#F43F5E" if label == "Telegram" else "#38BDF8"
            
            lbl_val = ctk.CTkLabel(row_f, text=val, font=("Segoe UI", 8, "bold"), text_color=val_fg, anchor="w")
            lbl_val.pack(side="left", fill="x", expand=True, padx=8, pady=6)
            
            if label == "GET DOMAIN":
                global lbl_domains_val
                lbl_domains_val = lbl_val
            elif label == "TIME":
                global lbl_time_val
                lbl_time_val = lbl_val
            elif label == "MS":
                global lbl_ms_val
                lbl_ms_val = lbl_val

if __name__ == "__main__":
    launcher = JKSYLauncherApp()
    launcher.mainloop()