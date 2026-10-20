"""JKSY Traffic: user-directed Google search and website inspection.

A dedicated headless Chrome session is created for this module. It never terminates
existing Chrome processes and does not automate repeat visits or fake traffic.
"""
from __future__ import annotations

import datetime
import os
import tempfile
import time
import threading
import urllib.parse
from tkinter import filedialog, messagebox

import customtkinter as ctk

BG = '#111111'
PANEL = '#191919'
GREEN = '#00ff66'
BLUE = '#1f538d'
RED = '#991b1b'


def open_window(parent):
    window = ctk.CTkToplevel(parent)
    window.title('JKSY • Traffic')
    window.geometry('1020x720')
    window.minsize(1000, 680)
    window.configure(fg_color=BG)
    window.after(90, lambda: (window.lift(), window.focus_force()))

    state = {'busy': False, 'closed': False, 'driver': None, 'profile': None,
             'lines': [], 'generation': 0, 'stop': threading.Event()}
    lock = threading.Lock()

    header = ctk.CTkFrame(window, fg_color=PANEL, corner_radius=10)
    header.pack(fill='x', padx=22, pady=(18, 12))
    ctk.CTkLabel(header, text='↗ JKSY TRAFFIC', text_color=GREEN,
                 font=('Segoe UI', 22, 'bold')).pack(pady=(14, 2))
    ctk.CTkLabel(header, text='Google Keyword Search • Headless Chrome • URL Inspection',
                 text_color='#b7c0c9', font=('Segoe UI', 12)).pack(pady=(0, 14))

    results = ctk.CTkFrame(window, fg_color=PANEL, corner_radius=10)
    results.pack(fill='both', expand=True, padx=22, pady=(0, 9))
    ctk.CTkLabel(results, text='▣ Traffic Session Log', text_color='#38bdf8',
                 font=('Segoe UI', 12, 'bold')).pack(anchor='w', padx=12, pady=(10, 5))
    out = ctk.CTkTextbox(results, fg_color='#000000', text_color=GREEN,
                         font=('Consolas', 12), wrap='word')
    out.pack(fill='both', expand=True, padx=12, pady=(0, 12))
    out.insert('end', '[SYSTEM] Ready • Traffic Testing (kunjungan ditandai jksy_test=1).\n')
    out.configure(state='disabled')
    form = ctk.CTkFrame(window, fg_color=PANEL, corner_radius=10)
    form.pack(fill='x', padx=22, pady=(0, 10))
    fields = ctk.CTkFrame(form, fg_color='transparent')
    fields.pack(fill='x', padx=12, pady=(10, 6))
    fields.grid_columnconfigure(0, weight=1)
    fields.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(fields, text='URL Tujuan', anchor='w', text_color='#bbc4cd').grid(row=0, column=0, sticky='ew', padx=(0, 6))
    ctk.CTkLabel(fields, text='Keyword Google', anchor='w', text_color='#bbc4cd').grid(row=0, column=1, sticky='ew', padx=(6, 0))
    url_entry = ctk.CTkEntry(fields, placeholder_text='https://example.com/', height=35)
    url_entry.grid(row=1, column=0, sticky='ew', padx=(0, 6), pady=(3, 0))
    keyword_entry = ctk.CTkEntry(fields, placeholder_text='Masukkan keyword pencarian', height=35)
    keyword_entry.grid(row=1, column=1, sticky='ew', padx=(6, 0), pady=(3, 0))

    settings = ctk.CTkFrame(form, fg_color='transparent')
    settings.pack(fill='x', padx=12, pady=(2, 10))
    ctk.CTkLabel(settings, text='User', text_color='#bbc4cd').pack(side='left', padx=(0, 6))
    user_var = ctk.StringVar(value='50')
    user_menu = ctk.CTkOptionMenu(settings, variable=user_var, values=['50', '100', 'Unlimited'],
                                   width=88, height=32, fg_color=BLUE, button_color='#143c68')
    user_menu.pack(side='left', padx=(0, 12))
    ctk.CTkLabel(settings, text='Delay', text_color='#bbc4cd').pack(side='left', padx=(0, 6))
    delay_var = ctk.StringVar(value='10')
    ctk.CTkOptionMenu(settings, variable=delay_var, values=['10', '30'],
                      width=75, height=32, fg_color=BLUE, button_color='#143c68').pack(side='left', padx=(0, 12))
    ctk.CTkLabel(settings, text='Mode', text_color='#bbc4cd').pack(side='left', padx=(0, 6))
    mode_var = ctk.StringVar(value='JKSY')
    ctk.CTkOptionMenu(settings, variable=mode_var, values=['JKSY', 'Organic'],
                      width=90, height=32, fg_color=BLUE, button_color='#143c68').pack(side='left')

    status = ctk.CTkLabel(window, text='READY • Browser otomatis tersembunyi', text_color='#b7c0c9', anchor='w')
    status.pack(fill='x', padx=24, pady=(0, 4))

    def log(message):
        if state['closed'] or not window.winfo_exists():
            return
        stamp = datetime.datetime.now().strftime('%H:%M:%S')
        line = f'[{stamp}] {message}'
        state['lines'].append(line)
        out.configure(state='normal')
        out.insert('end', line + '\n')
        out.see('end')
        out.configure(state='disabled')

    def set_busy(busy, text):
        if state['closed'] or not window.winfo_exists():
            return
        state['busy'] = busy
        test_btn.configure(state='disabled' if busy else 'normal')
        stop_btn.configure(state='normal' if busy else 'disabled')
        status.configure(text=text)

    def ui(fn):
        if not state['closed']:
            try:
                window.after(0, lambda: fn() if not state['closed'] else None)
            except RuntimeError:
                pass

    def valid_url(value):
        if not value:
            return None
        if '://' not in value:
            value = 'https://' + value
        p = urllib.parse.urlsplit(value)
        if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password:
            return None
        return value

    def get_driver():
        with lock:
            if state['driver'] is not None:
                try:
                    _ = state['driver'].current_url
                    return state['driver']
                except Exception:
                    try:
                        state['driver'].quit()
                    except Exception:
                        pass
                    state['driver'] = None
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
            except ImportError as exc:
                raise RuntimeError('Selenium belum terpasang. Jalankan: pip install selenium') from exc
            profile = tempfile.TemporaryDirectory(prefix='jksy_traffic_chrome_')
            options = Options()
            options.add_argument('--user-data-dir=' + profile.name)
            options.add_argument('--no-first-run')
            options.add_argument('--no-default-browser-check')
            options.add_argument('--window-size=1200,850')
            options.add_argument('--headless=new')
            # Chrome berjalan tanpa jendela, menggunakan profil sementara terpisah.
            try:
                driver = webdriver.Chrome(options=options)
                driver.set_page_load_timeout(30)
            except Exception:
                profile.cleanup()
                raise
            state['profile'] = profile
            state['driver'] = driver
            return driver

    def run_action(kind):
        if state['busy']:
            return
        keyword = keyword_entry.get().strip()
        target = valid_url(url_entry.get().strip())
        if kind == 'google' and not keyword:
            messagebox.showwarning('Traffic', 'Masukkan keyword Google.', parent=window)
            return
        if kind == 'visit' and not target:
            messagebox.showwarning('Traffic', 'Masukkan URL tujuan HTTP/HTTPS yang valid.', parent=window)
            return
        dest = 'https://www.google.com/search?' + urllib.parse.urlencode({'q': keyword}) if kind == 'google' else target
        set_busy(True, 'RUNNING • Chrome berjalan di latar belakang...')
        log('[OPEN] ' + ('Google keyword: ' + keyword if kind == 'google' else 'URL: ' + target))
        def worker():
            try:
                driver = get_driver()
                driver.get(dest)
                current_url = driver.current_url
                title = driver.title or '(tanpa judul)'
                ui(lambda: (log('[SUCCESS] Halaman berhasil dimuat'), log('[TITLE] ' + title),
                            log('[URL] ' + current_url),
                            set_busy(False, 'READY • Chrome JKSY berjalan di latar belakang')))
            except Exception as exc:
                ui(lambda: (log('[ERROR] ' + str(exc)), set_busy(False, 'ERROR • Periksa konfigurasi Chrome/Selenium')))
        threading.Thread(target=worker, daemon=True).start()

    def run_test():
        """Bounded, tagged navigation testing on an authorized site."""
        if state['busy']:
            return
        target = valid_url(url_entry.get().strip())
        if not target:
            messagebox.showwarning('Traffic', 'Masukkan URL tujuan yang valid.', parent=window)
            return
        if mode_var.get() == 'Organic':
            messagebox.showinfo('Traffic', 'Mode Organic tidak tersedia untuk simulasi pengunjung. Gunakan JKSY untuk pengujian bertanda.', parent=window)
            return
        if user_var.get() == 'Unlimited':
            messagebox.showinfo('Traffic', 'Unlimited tidak tersedia. Pengujian dibatasi hingga 100 sesi per rangkaian.', parent=window)
            return
        count = int(user_var.get())
        delay = int(delay_var.get())
        if not messagebox.askyesno('Traffic Testing',
                                  f'Jalankan {count} sesi pengujian bertanda dengan jeda {delay} detik\n'
                                  'hanya pada website yang kamu miliki/kelola?', parent=window):
            return
        p = urllib.parse.urlsplit(target)
        query = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
        query = [(k, v) for k, v in query if k != 'jksy_test']
        query.append(('jksy_test', '1'))
        test_url = urllib.parse.urlunsplit((p.scheme, p.netloc, p.path,
                                             urllib.parse.urlencode(query), p.fragment))
        state['stop'].clear()
        set_busy(True, 'RUNNING • JKSY Traffic Testing Mode')
        keyword = keyword_entry.get().strip()
        log(f'[TEST START] JKSY • {count} sesi • delay {delay}s • {test_url}')
        if keyword:
            log(f'[KEYWORD] {keyword} (referensi pengujian, bukan simulasi organic search)')

        def worker():
            passed = failed = 0
            for i in range(count):
                if state['stop'].is_set():
                    break
                try:
                    driver = get_driver()
                    driver.get(test_url)
                    title = driver.title or '(tanpa judul)'
                    passed += 1
                    ui(lambda i=i, title=title: log(f'[SUCCESS] Test {i+1}/{count} • {title}'))
                except Exception as exc:
                    failed += 1
                    ui(lambda i=i, exc=exc: log(f'[FAILED] Test {i+1}/{count} • {exc}'))
                if i + 1 < count and state['stop'].wait(delay):
                    break
            ui(lambda: (log(f'[DONE] Success: {passed} | Failed: {failed}' +
                            (' | STOPPED' if state['stop'].is_set() else '')),
                        set_busy(False, 'READY • Pengujian selesai')))
        threading.Thread(target=worker, daemon=True).start()

    def stop_test():
        state['stop'].set()
        status.configure(text='STOPPING • Menghentikan setelah navigasi berjalan selesai')

    def clear():
        state['lines'].clear()
        out.configure(state='normal')
        out.delete('1.0', 'end')
        out.configure(state='disabled')
        status.configure(text='READY • Log dibersihkan')

    def export():
        if not state['lines']:
            messagebox.showinfo('Traffic', 'Belum ada hasil untuk diekspor.', parent=window)
            return
        path = filedialog.asksaveasfilename(parent=window, defaultextension='.txt',
                                            filetypes=[('Text files', '*.txt')],
                                            initialfile='jksy-traffic-log.txt')
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as stream:
                    stream.write('\n'.join(state['lines']) + '\n')
                status.configure(text='SAVED • ' + path)
            except OSError as exc:
                messagebox.showerror('Export', str(exc), parent=window)

    def close():
        if state['closed']:
            return
        state['closed'] = True
        state['stop'].set()
        window.destroy()
        def cleanup():
            with lock:
                driver, profile = state['driver'], state['profile']
                if driver is not None:
                    try:
                        driver.quit()  # Hanya proses Chrome yang dibuat tool ini.
                    except Exception:
                        pass
                if profile is not None:
                    try:
                        profile.cleanup()
                    except Exception:
                        pass
        threading.Thread(target=cleanup, daemon=True).start()

    actions = ctk.CTkFrame(settings, fg_color='transparent')
    actions.pack(side='right', padx=(8, 0))
    test_btn = ctk.CTkButton(actions, text='Start', width=70, height=32,
                             fg_color='#2b8a3e', command=run_test)
    test_btn.pack(side='left', padx=(0, 5))
    stop_btn = ctk.CTkButton(actions, text='Stop', width=58, height=32, state='disabled',
                             fg_color=RED, command=stop_test)
    stop_btn.pack(side='left', padx=(0, 5))
    ctk.CTkButton(actions, text='Clear', width=60, height=32, fg_color='#555555', command=clear).pack(side='left', padx=(0, 5))
    ctk.CTkButton(actions, text='Export', width=65, height=32, fg_color=BLUE, command=export).pack(side='left', padx=(0, 5))
    ctk.CTkButton(actions, text='← Kembali', width=83, height=32, fg_color=RED, command=close).pack(side='right')
    url_entry.bind('<Return>', lambda _event: run_test())
    window.protocol('WM_DELETE_WINDOW', close)
    return window
