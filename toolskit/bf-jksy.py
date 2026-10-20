"""JKSY Website Login Inspector + offline password list audit."""
import tkinter as tk
import customtkinter as ctk

def open_window(parent):
    """Tampilkan Website Login Tester langsung dari tombol Brute Force launcher."""
    return open_website_tester(parent)


# Website Login Security Tester: one authorized test account, one submission per click.
from html.parser import HTMLParser
from tkinter import filedialog
from pathlib import Path
from collections import Counter
import hashlib
import hmac
import threading
from urllib.parse import urljoin, urlparse
import requests


class _LoginFormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == 'form':
            self.current = {'method': attrs.get('method', 'GET').upper(),
                            'action': attrs.get('action', ''), 'inputs': []}
            self.forms.append(self.current)
        elif tag.lower() == 'input' and self.current is not None:
            self.current['inputs'].append({
                'name': attrs.get('name', ''),
                'type': attrs.get('type', 'text').lower(),
                'value': attrs.get('value', ''),
                'autocomplete': attrs.get('autocomplete', '')
            })
        elif tag.lower() == 'button' and self.current is not None and attrs.get('name'):
            self.current['inputs'].append({
                'name': attrs['name'], 'type': 'submit', 'value': attrs.get('value', ''),
                'autocomplete': ''
            })

    def handle_endtag(self, tag):
        if tag.lower() == 'form':
            self.current = None


def _same_origin(url_a, url_b):
    a, b = urlparse(url_a), urlparse(url_b)
    return (a.scheme, a.hostname, a.port or (443 if a.scheme == 'https' else 80)) == (
        b.scheme, b.hostname, b.port or (443 if b.scheme == 'https' else 80))


def _validate_url(value):
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('URL harus HTTPS dan tidak memuat username/password.')
    return url


def _detect_login_form(html, url):
    parser = _LoginFormParser()
    parser.feed(html)
    matches = [f for f in parser.forms if any(i['type'] == 'password' for i in f['inputs'])]
    if not matches:
        return None
    form = matches[0]
    action = urljoin(url, form['action'])
    if not _same_origin(url, action):
        raise ValueError('Action form berada di origin lain; pengiriman diblokir.')
    if urlparse(action).scheme != 'https':
        raise ValueError('Form mengirim data ke HTTP tidak aman; pengiriman diblokir.')
    form['action_url'] = action
    pwd = next((i for i in form['inputs'] if i['type'] == 'password' and i['name']), None)
    candidates = [i for i in form['inputs'] if i['name'] and i['type'] in ('text', 'email')]
    form['username_field'] = (candidates[0]['name'] if candidates else '')
    form['password_field'] = pwd['name'] if pwd else ''
    return form


def _audit_password_file(filepath):
    """Read passwords locally; return aggregate counts only, never retain credentials."""
    path = Path(filepath)
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError('File terlalu besar (maksimum 5 MB).')
    total = 0
    unique = set()
    short = 0
    common = 0
    by_length = Counter()
    weak_words = {'password', '123456', '12345678', 'qwerty', 'admin', 'admin123', 'password123', '123456789', '111111', '123123'}
    with path.open('r', encoding='utf-8-sig') as f:
        for line in f:
            password = line.rstrip('\r\n')
            if not password:
                continue
            total += 1
            if total > 100000:
                raise ValueError('File melebihi 100.000 baris password.')
            unique.add(password)
            by_length[len(password)] += 1
            short += len(password) < 12
            common += password.lower() in weak_words
    return {
        'total': total, 'unique': len(unique), 'duplicates': total - len(unique),
        'short': short, 'common': common,
        'length_min': min(by_length, default=0), 'length_max': max(by_length, default=0)
    }


# Hash dengan salt statis mengurangi keterbacaan kunci pada source,
# tetapi BUKAN proteksi terhadap orang yang dapat memodifikasi kode.
_AUTH_SALT = b'jksy-auth-local-v1'
_AUTH_DIGEST = "c5c4ced7b5f5f985d777aee06c9c744cf5142219fb1f4e9e0da1dbfc8e761fec"


def _auth_matches(candidate):
    digest = hashlib.sha256(_AUTH_SALT + candidate.encode('utf-8')).hexdigest()
    return hmac.compare_digest(digest, _AUTH_DIGEST)


def _audit_user_file(filepath):
    """Hanya hitung statistik nama pengguna, tanpa memunculkan isi file."""
    path = Path(filepath)
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError('File terlalu besar (maksimum 5 MB).')
    users = []
    with path.open('r', encoding='utf-8-sig') as handle:
        for line in handle:
            username = line.strip()
            if username:
                users.append(username)
                if len(users) > 100000:
                    raise ValueError('File melebihi 100.000 baris.')
    return {'total': len(users), 'unique': len(set(users)),
            'duplicates': len(users) - len(set(users))}


def open_website_tester(parent):
    panel = ctk.CTkToplevel(parent)
    panel.title('JKSY • Website Login Security Inspector')
    panel.geometry('800x650')
    panel.minsize(780, 610)
    panel.configure(fg_color='#090D16')
    panel.transient(parent)

    header = ctk.CTkFrame(panel, fg_color='#0F172A', corner_radius=12)
    header.pack(fill='x', padx=15, pady=(12, 7))
    ctk.CTkLabel(header, text='🌐 JKSY WEBSITE LOGIN TESTER', font=('Segoe UI', 19, 'bold'),
                 text_color='#38BDF8').pack(anchor='w', padx=15, pady=(11, 2))
    ctk.CTkLabel(header, text='Inspect form login dan analisis kredensial lokal (tanpa uji password massal)',
                 text_color='#94A3B8').pack(anchor='w', padx=15, pady=(0, 10))

    form_box = ctk.CTkFrame(panel, fg_color='#0F172A', corner_radius=12)
    form_box.pack(fill='x', padx=15, pady=(0, 8))
    ctk.CTkLabel(form_box, text='Login URL (HTTPS)', text_color='#CBD5E1').pack(anchor='w', padx=14, pady=(10, 3))
    url_input = ctk.CTkEntry(form_box, placeholder_text='Input Link', height=35,
                             fg_color='#090D16', border_color='#334155')
    url_input.pack(fill='x', padx=14, pady=(0, 8))

    creds = ctk.CTkFrame(form_box, fg_color='transparent')
    creds.pack(fill='x', padx=14, pady=(0, 7))
    username_input = ctk.CTkEntry(creds, placeholder_text='Input User', height=34, fg_color='#090D16')
    username_input.pack(side='left', expand=True, fill='x', padx=(0, 6))
    password_input = ctk.CTkEntry(creds, placeholder_text='Input Password', show='●', height=34,
                                  fg_color='#090D16')
    password_input.pack(side='left', expand=True, fill='x', padx=(6, 0))

    imports = ctk.CTkFrame(form_box, fg_color='transparent')
    imports.pack(fill='x', padx=14, pady=(0, 7))
    import_user_btn = ctk.CTkButton(imports, text='Import User', fg_color='#1D4ED8',
                                    hover_color='#1E40AF', width=170)
    import_user_btn.pack(side='left', padx=(0, 8))
    import_pass_btn = ctk.CTkButton(imports, text='Import Pass', fg_color='#1D4ED8',
                                    hover_color='#1E40AF', width=190)
    import_pass_btn.pack(side='left')
    file_label = ctk.CTkLabel(imports, text='Belum ada file', text_color='#94A3B8', anchor='e')
    file_label.pack(side='right', fill='x', expand=True)

    lock_row = ctk.CTkFrame(form_box, fg_color='transparent')
    lock_row.pack(fill='x', padx=14, pady=(0, 10))
    auth_btn = ctk.CTkButton(lock_row, text='🔒 Auth Key', fg_color='#7C3AED',
                             hover_color='#6D28D9', width=130)
    auth_btn.pack(side='left')
    auth_status = ctk.CTkLabel(lock_row, text='Fitur khusus: TERKUNCI', text_color='#FBBF24')
    auth_status.pack(side='left', padx=12)

    log = ctk.CTkTextbox(panel, fg_color='#0F172A', text_color='#34D399',
                         font=('Consolas', 11), wrap='word')
    log.pack(fill='both', expand=True, padx=15, pady=(0, 8))
    log.insert('end', 'JKSY Security Inspector siap.\n'
               'Inspect Login memeriksa halaman HTTPS tanpa mengirim kredensial.\n'
               'Import TXT dianalisis offline; isi password tidak dikirim ke situs.\n')
    log.configure(state='disabled')

    state = {'busy': False, 'authorized': False, 'user_report': None,
             'password_report': None, 'speed': 'Speed'}

    def write(message):
        if not panel.winfo_exists():
            return
        log.configure(state='normal')
        log.insert('end', message + '\n')
        log.see('end')
        log.configure(state='disabled')

    def update_files_label():
        u = state['user_report']
        p = state['password_report']
        file_label.configure(text=f"User: {u['total'] if u else 0} | Password: {p['total'] if p else 0}")

    def import_user_txt():
        filepath = filedialog.askopenfilename(parent=panel, title='Import User TXT',
                                              filetypes=[('Text Files', '*.txt')])
        if not filepath:
            return
        try:
            report = _audit_user_file(filepath)
            state['user_report'] = report
            update_files_label()
            write(f"[IMPORT USER] {Path(filepath).name}: total={report['total']}, "
                  f"unik={report['unique']}, duplikat={report['duplicates']} (offline)")
        except (OSError, UnicodeError, ValueError) as exc:
            write('Import user gagal: ' + str(exc))

    def import_password_txt():
        filepath = filedialog.askopenfilename(parent=panel, title='Import Password TXT',
                                              filetypes=[('Text Files', '*.txt')])
        if not filepath:
            return
        try:
            report = _audit_password_file(filepath)
            state['password_report'] = report
            update_files_label()
            write(f"[IMPORT PASSWORD] {Path(filepath).name}: total={report['total']}, "
                  f"unik={report['unique']}, duplikat={report['duplicates']}, "
                  f"pendek(<12)={report['short']}, umum={report['common']} (offline)")
        except (OSError, UnicodeError, ValueError) as exc:
            write('Import password gagal: ' + str(exc))

    import_user_btn.configure(command=import_user_txt)
    import_pass_btn.configure(command=import_password_txt)

    def open_auth_dialog():
        dialog = ctk.CTkToplevel(panel)
        dialog.title('JKSY • Auth Key')
        dialog.geometry('365x200')
        dialog.resizable(False, False)
        dialog.transient(panel)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text='Unlock Special Mode', font=('Segoe UI', 15, 'bold')).pack(pady=(16, 9))
        key_field = ctk.CTkEntry(dialog, placeholder_text='Masukkan Auth Key', show='●', width=290)
        key_field.pack(pady=(0, 10))
        feedback = ctk.CTkLabel(dialog, text='', text_color='#F87171')
        feedback.pack()
        def validate():
            value = key_field.get()
            key_field.delete(0, 'end')
            if _auth_matches(value):
                state['authorized'] = True
                auth_status.configure(text='Fitur khusus: UNLOCKED', text_color='#34D399')
                auth_btn.configure(text='🔓 Auth Key')
                write('[AUTH] Fitur khusus analisis lokal telah dibuka.')
                dialog.destroy()
            else:
                feedback.configure(text='Auth Key tidak valid.')
        key_field.bind('<Return>', lambda _event: validate())
        ctk.CTkButton(dialog, text='Unlock', command=validate, width=160).pack(pady=(5, 0))
        key_field.focus_set()
    auth_btn.configure(command=open_auth_dialog)

    def speed_changed(choice):
        if choice == 'Lock':
            state['speed'] = 'Lock'
            write('[SPEED] Mode lokal dinonaktifkan.')
        elif choice in ('Speed 50', 'Speed 100') and not state['authorized']:
            write('[SPEED] Pilihan ini terkunci. Masukkan Auth Key dahulu.')
            speed_menu.set(state['speed'])
        else:
            state['speed'] = choice
            write(f'[SPEED] {choice} dipilih untuk mode analisis lokal. Tidak mengatur request login.')

    def set_busy(value):
        state['busy'] = value
        inspect_btn.configure(state='disabled' if value else 'normal')
        attack_btn.configure(state='disabled' if value else 'normal')
        import_user_btn.configure(state='disabled' if value else 'normal')
        import_pass_btn.configure(state='disabled' if value else 'normal')

    def on_done(message):
        if panel.winfo_exists():
            write(message)
            set_busy(False)

    def run_inspect():
        if state['busy']:
            return
        try:
            target = _validate_url(url_input.get())
        except ValueError as exc:
            write('ERROR: ' + str(exc))
            return
        set_busy(True)
        write('\n[INSPECT LOGIN] ' + target)

        def worker():
            try:
                response = requests.get(target, timeout=12, allow_redirects=False,
                                        headers={'User-Agent': 'JKSY-Security-Inspector/1.0'})
                lines = [f'GET HTTP {response.status_code}',
                         f'HSTS: {response.headers.get("Strict-Transport-Security", "tidak terdeteksi")}',
                         f'Content-Security-Policy: {"tersedia" if response.headers.get("Content-Security-Policy") else "tidak terdeteksi"}',
                         f'X-Frame-Options: {response.headers.get("X-Frame-Options", "tidak terdeteksi")}']
                if response.cookies:
                    for cookie in response.cookies:
                        lines.append(f'Cookie {cookie.name}: Secure={cookie.secure}; '
                                     f'HttpOnly={"HttpOnly" in cookie._rest}; '
                                     f'SameSite={cookie._rest.get("SameSite", "tidak terdeteksi")}')
                else:
                    lines.append('Cookie: tidak ada pada respons halaman')
                if response.is_redirect:
                    lines.append('Redirect: ' + response.headers.get('Location', '?'))
                    lines.append('Inspect berhenti pada redirect (tidak mengikuti otomatis).')
                else:
                    form = _detect_login_form(response.text, target)
                    if form:
                        lines.append('Form method: ' + form['method'])
                        lines.append('Form action: ' + form['action_url'])
                        lines.append('Field username: ' + (form['username_field'] or '(belum terdeteksi)'))
                        lines.append('Field password: ' + (form['password_field'] or '(belum terdeteksi)'))
                        lines.append('Input hidden: ' + ', '.join(i['name'] for i in form['inputs']
                                                                  if i['type'] == 'hidden' and i['name']))
                    else:
                        lines.append('Form password tidak ditemukan di HTML; mungkin menggunakan JavaScript.')
                message = '\n'.join(lines)
            except Exception as exc:
                message = 'Inspect gagal: ' + str(exc)
            try:
                panel.after(0, lambda m=message: on_done(m))
            except tk.TclError:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def clear_log():
        if state['busy']:
            return
        log.configure(state='normal')
        log.delete('1.0', 'end')
        log.configure(state='disabled')

    def export_log():
        # Hanya ekspor log ringkasan; password dan isi file TXT tidak dicatat.
        content = log.get('1.0', 'end-1c')
        if not content.strip():
            write('[EXPORT] Log kosong. Tidak ada hasil untuk disimpan.')
            return
        filepath = filedialog.asksaveasfilename(
            parent=panel, title='Simpan Hasil Pemeriksaan',
            defaultextension='.txt',
            filetypes=[('Text Files', '*.txt')],
            initialfile='jksy-inspection-results.txt')
        if not filepath:
            return
        try:
            Path(filepath).write_text(content + '\n', encoding='utf-8')
            write('[EXPORT] Hasil log tersimpan: ' + str(Path(filepath).name))
        except OSError as exc:
            write('[EXPORT] Gagal menyimpan: ' + str(exc))

    def run_attack():
        """One-time, non-invasive audit; does NOT submit imported credentials."""
        if state['busy']:
            return
        if state['speed'] == 'Lock':
            write('[RUN] Mode Lock aktif. Pilih Speed terlebih dahulu.')
            return
        write('\n[RUN] Memulai audit keamanan (tanpa percobaan brute force/login massal).')
        write('[RUN] Speed: ' + state['speed'] + ' — pilihan mode lokal, bukan kecepatan request.')
        u = state['user_report']
        p = state['password_report']
        if u:
            write(f"[USER] Total: {u['total']} | Unik: {u['unique']} | Duplikat: {u['duplicates']}")
        if p:
            write(f"[PASSWORD] Total: {p['total']} | Unik: {p['unique']} | "
                  f"Duplikat: {p['duplicates']} | Pendek: {p['short']} | Umum: {p['common']}")
        if username_input.get().strip():
            write('[USER] Input manual tersedia (isinya tidak dicatat).')
        if password_input.get():
            write('[PASSWORD] Input manual tersedia (isinya tidak dicatat atau dikirim).')
        if url_input.get().strip():
            run_inspect()
        else:
            write('[RUN] Selesai. Input Link kosong; tidak ada inspeksi website.')

    buttons = ctk.CTkFrame(panel, fg_color='transparent')
    buttons.pack(fill='x', padx=15, pady=(0, 14))
    inspect_btn = ctk.CTkButton(buttons, text='Inspect', fg_color='#059669',
                                command=run_inspect, width=145)
    inspect_btn.pack(side='left', padx=(0, 9))
    speed_menu = ctk.CTkOptionMenu(buttons, values=['Speed', 'Speed 5', 'Speed 10',
                                                    'Lock', 'Speed 50', 'Speed 100'],
                                    command=speed_changed, width=140,
                                    fg_color='#334155', button_color='#475569')
    speed_menu.set('Speed')
    speed_menu.pack(side='left')
    attack_btn = ctk.CTkButton(buttons, text='Attack', fg_color='#B45309',
                                hover_color='#92400E', command=run_attack, width=110)
    attack_btn.pack(side='left', padx=(9, 0))
    ctk.CTkButton(buttons, text='← Kembali', fg_color='#991B1B',
                  command=panel.destroy, width=110).pack(side='right')
    ctk.CTkButton(buttons, text='Export', fg_color='#1D4ED8',
                  command=export_log, width=95).pack(side='right', padx=(0, 7))
    ctk.CTkButton(buttons, text='Clear', fg_color='#475569',
                  command=clear_log, width=90).pack(side='right', padx=(0, 7))
    return panel


if __name__ == '__main__':
    print('ACCESS DENIED: Modul ini hanya tersedia melalui aplikasi.py.')
    raise SystemExit(1)
