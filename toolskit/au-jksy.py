"""JKSY Ahrefs domain / URL report, API v3. Token fetched from operator public GitHub URL."""
import csv
import datetime as dt
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Alamat layanan dikemas untuk mengurangi keterbacaan string pada source.
# Ini bukan perlindungan rahasia: URL dapat dipulihkan saat program berjalan.
import base64 as _b64
import zlib as _zl

def _endpoint(encoded):
    mask = bytes.fromhex('7ac33051d98fb20464e173ab1d9907f2')
    raw = _b64.b85decode(encoded)
    packed = bytes(value ^ mask[index % len(mask)] for index, value in enumerate(raw))
    return _zl.decompress(packed).decode('utf-8')

API_BASE = _endpoint('0vY>x@TQuwwl+M6)lE!3Qi*+f55#=SvCcq!GFL0Rua2F05k{R(N#k>{hnI5')
TOKEN_URL = _endpoint('0vRQln1M1RXyvoK)E}(H<&lvK`41Bz;y!3hCHwIjbk9nRM8i})@ur(*r2q_1Sdty%Wyo%JwPdn9Uje01D5(gwMu1RDeiH')


def get_ahrefs_token():
    """Fetch owner-published token at scan time (public URL; not a security boundary)."""
    req = urllib.request.Request(TOKEN_URL, headers={'User-Agent': 'JKSY-Ahrefs/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            token = response.read(4096).decode('utf-8').strip()
    except (urllib.error.URLError, UnicodeError) as exc:
        raise RuntimeError('Gagal mengambil konfigurasi Ahrefs dari GitHub: ' + str(exc)) from None
    if not token or any(char.isspace() for char in token) or len(token) > 512:
        raise RuntimeError('Format API token pada GitHub tidak valid.')
    return token
COLOR_GREEN = '#2b8a3e'
COLOR_BLUE = '#1f538d'
COLOR_RED = '#991B1B'


def normalize_target(raw):
    raw = raw.strip()
    if not raw or any(ch.isspace() for ch in raw):
        raise ValueError('Masukkan domain atau URL yang valid.')
    url = raw if '://' in raw else 'https://' + raw
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('URL harus memakai http:// atau https://.')
    if parsed.username or parsed.password:
        raise ValueError('URL dengan kredensial tidak didukung.')
    host = parsed.hostname.lower().rstrip('.')
    if '.' not in host or len(host) > 253:
        raise ValueError('Domain tidak valid.')
    if parsed.port:
        raise ValueError('Port khusus tidak didukung.')
    suffix = (parsed.path or '/') + (('?' + parsed.query) if parsed.query else '')
    return host, url, suffix != '/'


class ApiError(RuntimeError):
    def __init__(self, status, details):
        self.status = status
        super().__init__(f'HTTP {status} dari Ahrefs: {details}')


def api_get(section, token, target, day, mode='subdomains'):
    args = {'target': target, 'date': day, 'output': 'json'}
    if section != 'domain-rating':
        args['mode'] = mode
    url = API_BASE + '/' + section + '?' + urllib.parse.urlencode(args)
    req = urllib.request.Request(url, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/json',
        'User-Agent': 'JKSY-Domain-Report/1.1',
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                payload = json.loads(response.read(1_000_000).decode('utf-8'))
                if not isinstance(payload, dict):
                    raise RuntimeError(f'Respons {section} bukan objek JSON.')
                return payload
        except urllib.error.HTTPError as exc:
            details = exc.read(1000).decode('utf-8', errors='replace').replace(token, '[REDACTED]')
            if exc.code in (500, 502, 503, 504, 429) and attempt < 2:
                retry_after = exc.headers.get('Retry-After', '')
                delay = min(6, max(1, int(retry_after))) if retry_after.isdecimal() else (attempt + 1) * 2
                time.sleep(delay)
                continue
            raise ApiError(exc.code, details[:260]) from None
        except urllib.error.URLError as exc:
            if attempt < 2:
                time.sleep(attempt + 1)
                continue
            raise RuntimeError('Gagal menghubungi API Ahrefs: ' + str(exc.reason)) from None


def _candidate_dates():
    # Terbaru dahulu. Data Ahrefs adalah snapshot, bukan statistik real-time.
    today = dt.datetime.now(dt.timezone.utc).date()
    for days_ago in (0, 1, 2, 3, 7, 14, 30):
        yield (today - dt.timedelta(days=days_ago)).isoformat()


def report_for(target, token, day, mode):
    report = {'target': target, 'date': day, 'mode': mode, 'data': {},
              'errors': {}, 'dates': {}, 'date_note': ''}
    candidates = list(dict.fromkeys([day, *_candidate_dates()]))
    sections = {'domain-rating': 'domain_rating', 'backlinks-stats': 'metrics', 'metrics': 'metrics'}
    for section, field in sections.items():
        # Masing-masing endpoint berbeda dalam ketersediaan datanya.
        # 500 tidak berarti masalah tanggal; jangan mencoba 30 tanggal hanya untuk 500.
        for candidate in candidates:
            try:
                payload = api_get(section, token, target, candidate, mode)
                value = payload.get(field)
                if not isinstance(value, dict):
                    raise RuntimeError(f'Respons Ahrefs {section} tidak berisi {field}.')
                report['data'][section] = value
                report['dates'][section] = candidate
                report['errors'].pop(section, None)
                break
            except ApiError as exc:
                report['errors'][section] = str(exc)
                if exc.status == 400 and 'bad date' in str(exc).lower():
                    continue
                break
            except Exception as exc:
                report['errors'][section] = str(exc)
                break
    used = sorted(set(report['dates'].values()))
    if used:
        report['date'] = max(used)
        report['date_note'] = ('Snapshot terbaru yang tersedia untuk masing-masing endpoint; '
                               'lihat tanggal pada tiap metrik.')
    else:
        report['date_note'] = 'Tidak ada data valid yang dikembalikan API.'
    return report


def pretty(value):
    if value is None:
        return 'N/A'
    if isinstance(value, int):
        return f'{value:,}'
    return str(value)


def format_report(report):
    d = report['data'].get('domain-rating', {})
    b = report['data'].get('backlinks-stats', {})
    m = report['data'].get('metrics', {})
    lines = [
        '=== JKSY • AUTHORITY REPORT ===',
        'Target             : ' + report['target'],
        'Tanggal terbaru    : ' + report['date'],
        'Noted              : Update',
        'Mode               : ' + report['mode'],
        'Data DR            : ' + report.get('dates', {}).get('domain-rating', 'N/A'),
        'Data Backlinks     : ' + report.get('dates', {}).get('backlinks-stats', 'N/A'),
        'Data Organic       : ' + report.get('dates', {}).get('metrics', 'N/A'),
        '-' * 55,
        'Domain Rating (DR) : ' + pretty(d.get('domain_rating')),
        'Ahrefs Rank        : ' + pretty(d.get('ahrefs_rank')),
        'Backlinks live     : ' + pretty(b.get('live')),
        'Ref. Domains live  : ' + pretty(b.get('live_refdomains')),
        'Backlinks all-time : ' + pretty(b.get('all_time')),
        'Ref. Domains total : ' + pretty(b.get('all_time_refdomains')),
        'Organic Traffic    : ' + pretty(m.get('org_traffic')),
        'Organic Keywords   : ' + pretty(m.get('org_keywords')),
        'Keywords Top 3     : ' + pretty(m.get('org_keywords_1_3')),
        'Traffic Value (USD): ' + (f"{m['org_cost'] / 100:,.2f}" if isinstance(m.get('org_cost'), (float, int)) else 'N/A'),
        '-' * 55,
    ]
    if report['errors']:
        lines += ['API ERROR / PARTIAL RESULTS:']
        lines += [f"  {section}: {error}" for section, error in report['errors'].items()]
    return '\n'.join(lines)


def open_window(parent):
    window = ctk.CTkToplevel(parent)
    window.title('JKSY • Authority')
    window.geometry('760x615')
    window.minsize(700, 555)
    window.configure(fg_color='#101010')
    window.transient(parent)
    window.lift()
    window.after(120, window.focus_force)
    result = {'last': None, 'busy': False}

    def close():
        window.destroy()
    window.protocol('WM_DELETE_WINDOW', close)

    ctk.CTkLabel(window, text='◆ JKSY AUTHORITY',
                 text_color='#00FF66', font=('Segoe UI', 19, 'bold')).pack(pady=(17, 4))
    ctk.CTkLabel(window, text='Domain Rating • Backlinks • Referring Domains • Organic Search',
                 text_color='#aab0b8', font=('Segoe UI', 11)).pack(pady=(0, 15))

    log = ctk.CTkTextbox(window, fg_color='#070707', text_color='#00ff66', font=('Consolas', 12), wrap='word')
    log.pack(fill='both', expand=True, padx=22, pady=(0, 10))
    log.insert('1.0', 'READY • Masukkan domain/URL kemudian klik Scan.\n')
    log.configure(state='disabled')

    row = ctk.CTkFrame(window, fg_color='transparent')
    row.pack(fill='x', padx=22, pady=(0, 9))
    target_entry = ctk.CTkEntry(row, placeholder_text='contoh.com / https://contoh.com/page', height=34)
    target_entry.pack(side='left', fill='x', expand=True, padx=(0, 8))
    mode_var = ctk.StringVar(value='Domain + Subdomain')
    choices = {'Domain + Subdomain': 'subdomains', 'Domain Saja': 'domain', 'URL Tepat': 'exact', 'URL Prefix': 'prefix'}
    ctk.CTkOptionMenu(row, variable=mode_var, values=list(choices), width=170,
                       fg_color=COLOR_BLUE, button_color='#16416b').pack(side='right')

    status = ctk.CTkLabel(window, text='READY', text_color='#aab0b8', anchor='w')
    status.pack(fill='x', padx=24, pady=(0, 7))

    def display(text):
        if not window.winfo_exists():
            return
        log.configure(state='normal')
        log.delete('1.0', 'end')
        log.insert('1.0', text)
        log.configure(state='disabled')

    def finish(report):
        result['busy'] = False
        result['last'] = report
        scan_btn.configure(state='normal')
        status.configure(text='DONE • ' + ('Partial results' if report['errors'] else 'Success'))
        display(format_report(report))

    def scan():
        if result['busy']:
            return
        try:
            host, url, has_path = normalize_target(target_entry.get())
        except ValueError as exc:
            messagebox.showwarning('Target invalid', str(exc), parent=window)
            return
        selected_mode = choices[mode_var.get()]
        if has_path and selected_mode in ('subdomains', 'domain'):
            messagebox.showwarning('Mode URL', 'Untuk URL dengan path, gunakan URL Tepat atau URL Prefix.', parent=window)
            return
        target = url if selected_mode in ('exact', 'prefix') else host
        result['busy'] = True
        result['last'] = None
        scan_btn.configure(state='disabled')
        status.configure(text='RUNNING • Memuat laporan Authority...')
        display('Mengambil data Authority...\n')
        def worker():
            try:
                token = get_ahrefs_token()
                data = report_for(target, token, (dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)).isoformat(), selected_mode)
                if window.winfo_exists():
                    window.after(0, lambda: finish(data))
            except Exception as exc:
                if window.winfo_exists():
                    window.after(0, lambda: fail(str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def fail(message):
        result['busy'] = False
        scan_btn.configure(state='normal')
        status.configure(text='ERROR')
        display('ERROR: ' + message)

    def export():
        if not result['last']:
            messagebox.showwarning('Export', 'Belum ada hasil scan.', parent=window)
            return
        path = filedialog.asksaveasfilename(parent=window, defaultextension='.txt',
                                             filetypes=[('Text report', '*.txt')], title='Export Authority Result')
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as file:
                file.write(format_report(result['last']) + '\n')
            status.configure(text='SAVED • ' + os.path.basename(path))
        except OSError as exc:
            messagebox.showerror('Export gagal', str(exc), parent=window)

    actions = ctk.CTkFrame(window, fg_color='transparent')
    actions.pack(pady=(0, 16))
    scan_btn = ctk.CTkButton(actions, text='Scan', width=110, fg_color=COLOR_GREEN, command=scan)
    scan_btn.pack(side='left', padx=6)
    ctk.CTkButton(actions, text='Clear', width=110, fg_color=COLOR_BLUE,
                  command=lambda: (display('READY\n'), status.configure(text='READY'), result.update(last=None))).pack(side='left', padx=6)
    ctk.CTkButton(actions, text='Export', width=110, fg_color=COLOR_BLUE, command=export).pack(side='left', padx=6)
    ctk.CTkButton(actions, text='Kembali', width=110, fg_color=COLOR_RED, command=close).pack(side='left', padx=6)
    target_entry.bind('<Return>', lambda e: scan())
    return window
