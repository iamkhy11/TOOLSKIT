"""JKSY Web Directory Auditor: limited, authorized single-target directory checks.
No webshell signatures, exploitation, credential attempts or arbitrary Internet discovery.
"""
import threading
import re
import hashlib
import os
import queue
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin, urldefrag, unquote
from urllib.request import Request, urlopen, build_opener
from urllib.error import HTTPError, URLError
import customtkinter as ctk
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from collections import deque, Counter
from tkinter import filedialog, messagebox

BG = '#111111'
PANEL = '#191919'
GREEN = '#2b8a3e'
BLUE = '#1f538d'
MAX_PATHS = 30
MAX_DISCOVERED = 1500
MAX_HTML_PAGES = 200
MAX_SITEMAPS = 60
MAX_BODY = 3_000_000
REQUEST_DELAY = 0.8
DEFAULT_PATHS = ['robots.txt', 'sitemap.xml', 'favicon.ico', 'assets/', 'static/', 'images/', 'css/', 'js/', 'docs/']


def validate_target(url):
    parsed = urlparse(url.strip())
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Target harus URL HTTPS, tanpa user/password.')
    if parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise ValueError('Gunakan origin website saja, misalnya https://contoh.com')
    return f'https://{parsed.netloc}/'


def validate_path(value):
    p = value.strip().lstrip('/')
    if not p or len(p) > 160 or '?' in p or '#' in p or '\\' in p:
        return None
    bits = p.split('/')
    if any(bit in ('.', '..') or not all(c.isalnum() or c in '-_.' for c in bit) for bit in bits if bit):
        return None
    return p




class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for attr in ('href', 'src'):
            value = attrs.get(attr)
            if value and tag.lower() in ('a', 'img', 'script', 'link', 'source', 'video', 'audio'):
                self.links.append(value)


def normalized_url(raw, base, origin):
    url = urldefrag(urljoin(base, raw.strip()))[0]
    p, expected = urlparse(url), urlparse(origin)
    if p.scheme != 'https' or p.netloc.lower() != expected.netloc.lower() or not p.path.startswith('/'):
        return None
    # Do not submit query strings or follow URLs that contain credentials.
    if p.username or p.password or p.query:
        return None
    return url


def fetch_public(url, method='GET'):
    """Return real HTTP response status, MIME type, safe body and Location.

    Redirects are not followed: 301/302/307/308 remain visible.
    """
    opener = build_opener(NoRedirect())
    req = Request(url, method=method, headers={
        'User-Agent': 'JKSY-Public-Directory-Audit/2.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml,text/xml,text/plain,*/*',
    })
    try:
        with opener.open(req, timeout=8) as response:
            data = response.read(MAX_BODY) if method == 'GET' else b''
            return response.status, response.headers.get('Content-Type', ''), data, response.headers.get('Location', '')
    except HTTPError as exc:
        return exc.code, exc.headers.get('Content-Type', ''), b'', exc.headers.get('Location', '')
    except (URLError, TimeoutError, OSError):
        return 'ERROR', '', b'', ''


def file_type(path, content_type):
    ext = Path(unquote(urlparse(path).path)).suffix.lower()
    if ext:
        return ext[1:].upper()
    mime = content_type.split(';', 1)[0].strip().lower()
    if 'html' in mime:
        return 'HTML'
    if 'json' in mime:
        return 'JSON'
    if 'xml' in mime:
        return 'XML'
    if mime.startswith('image/'):
        return 'IMAGE'
    if mime.startswith('text/'):
        return 'TEXT'
    return 'DIRECTORY' if urlparse(path).path.endswith('/') else (mime or 'UNKNOWN')


def public_discovery(origin, cancel, emit):
    """Explore linked public URLs and published sitemaps on one HTTPS origin.

    Does not guess URLs, enumerate private filesystem entries, or execute code.
    """
    visited = set()
    queued = set()
    found = []
    to_check = deque()
    sitemap_seen = set()
    html_seen = 0
    status_counts = Counter()

    def enqueue(url, sitemap=False):
        if not url or url in visited or url in queued:
            return
        # Hard cap prevents enormous sitemap indices from exhausting memory.
        if len(queued) + len(visited) >= MAX_DISCOVERED * 4:
            return
        if sitemap:
            if url not in sitemap_seen and len(sitemap_seen) >= MAX_SITEMAPS:
                return
            sitemap_seen.add(url)
        queued.add(url)
        to_check.append(url)

    enqueue(origin)
    enqueue(urljoin(origin, 'robots.txt'))
    enqueue(urljoin(origin, 'sitemap.xml'), sitemap=True)
    while to_check and len(visited) < MAX_DISCOVERED and not cancel.is_set():
        url = to_check.popleft()
        queued.discard(url)
        if url in visited:
            continue
        visited.add(url)
        status, ctype, body, location = fetch_public(url)
        relpath = urlparse(url).path.lstrip('/') or '/'
        item = {'path': relpath, 'status': str(status), 'type': file_type(url, ctype), 'source': 'PUBLIC', 'content_type': ctype, 'location': location}
        status_counts[str(status)] += 1
        found.append(item)
        emit('result', item)
        if len(visited) == 1 or len(visited) % 10 == 0:
            emit('status', f'[RUNNING] [PUBLIC] {len(visited)} URL | {html_seen} HTML | {len(sitemap_seen)} Sitemap')
        if status == 200 and body:
            if relpath == 'robots.txt':
                for line in body.decode('utf-8', 'replace').splitlines():
                    if line.lower().startswith('sitemap:'):
                        enqueue(normalized_url(line.split(':', 1)[1], url, origin), sitemap=True)
            if 'xml' in ctype.lower() or relpath.lower().endswith('.xml'):
                try:
                    root = ET.fromstring(body)
                    for node in root.iter():
                        if node.tag.rsplit('}', 1)[-1].lower() != 'loc' or not node.text:
                            continue
                        link = normalized_url(node.text, url, origin)
                        if link:
                            enqueue(link, sitemap=urlparse(link).path.lower().endswith('.xml'))
                except ET.ParseError:
                    pass
            if 'html' in ctype.lower() and html_seen < MAX_HTML_PAGES:
                html_seen += 1
                parser = LinkParser()
                try:
                    parser.feed(body.decode('utf-8', 'replace'))
                except Exception:
                    pass
                for value in parser.links:
                    enqueue(normalized_url(value, url, origin))
        cancel.wait(REQUEST_DELAY)
    reason = ('DIBATALKAN' if cancel.is_set() else
              'BATAS TERCAPAI' if len(visited) >= MAX_DISCOVERED else 'ANTRIAN HABIS')
    summary = ' | '.join(f'{code}: {count}' for code, count in sorted(status_counts.items()))
    emit('status', f'[DISCOVERY DONE] {len(visited)} URL diperiksa | {reason}')
    emit('status', '[HTTP SUMMARY] ' + (summary or 'Tidak ada respons'))


# CMS fingerprinting uses publicly visible evidence only, without login or probing hidden paths.
CMS_MARKERS = {
    'WordPress': (r'wp-content/', r'wp-includes/', r'<meta[^>]+generator[^>]+wordpress'),
    'Joomla': (r'/media/system/', r'/media/com_', r'<meta[^>]+generator[^>]+joomla'),
    'Drupal': (r'/sites/default/files/', r'/core/misc/', r'drupal-settings-json'),
    'Magento': (r'/static/version[^/]+/', r'/pub/static/', r'mage/cookies'),
    'Shopify': (r'cdn\.shopify\.com', r'shopify-section', r'shopify-payment-button'),
    'Ghost': (r'ghost-portal', r'content/images/', r'<meta[^>]+generator[^>]+ghost'),
}


def fingerprint_cms(html, headers=None):
    text = html.lower()
    hits = {}
    for cms, patterns in CMS_MARKERS.items():
        matches = [p for p in patterns if re.search(p, text, re.I)]
        if matches:
            hits[cms] = len(matches)
    if not hits:
        return 'Unknown / Custom', 'LOW', 'Tidak ditemukan indikator CMS yang cukup'
    highest = max(hits.values())
    winners = [cms for cms, count in hits.items() if count == highest]
    if len(winners) > 1:
        return 'Ambiguous: ' + ', '.join(winners), 'LOW', 'Indikator beberapa CMS terdeteksi'
    return winners[0], 'MEDIUM' if highest >= 2 else 'LOW', f'{highest} indikator publik'


def scan_cms(origin, cancel, emit):
    if cancel.is_set():
        return
    status, ctype, body, location = fetch_public(origin)
    if status != 200 or 'html' not in ctype.lower():
        emit('status', f'[CMS] Tidak dapat mendeteksi dari halaman utama (HTTP {status}; {ctype or "tanpa Content-Type"})')
        return
    cms, confidence, reason = fingerprint_cms(body[:MAX_BODY].decode('utf-8', 'replace'))
    emit('status', f'[CMS] {cms} • Confidence: {confidence} • {reason}')
    emit('result', {'path': '/', 'status': str(status), 'type': 'HTML', 'source': 'CMS FINGERPRINT', 'reason': f'{cms}; {confidence}; {reason}', 'content_type': ctype, 'location': location})


def cms_discovery(origin, cancel, emit):
    # Find linked publicly exposed resources, not private files or guessed webshell names.
    scan_cms(origin, cancel, emit)
    if not cancel.is_set():
        public_discovery(origin, cancel, emit)

# Defensive filesystem inventory: only directories accessible to the operator.
# No file execution, exploit probes, or remote webshell hunting.
SUSPICIOUS_RULES = (
    ('dynamic execution', re.compile(rb"\b(?:eval|assert)\s*\(\s*(?:\$_(?:POST|GET|REQUEST|COOKIE)|base64_decode\s*\()", re.I)),
    ('command execution from input', re.compile(rb"\b(?:system|exec|shell_exec|passthru|proc_open|popen)\s*\(\s*\$_(?:GET|POST|REQUEST|COOKIE)", re.I)),
    ('obfuscated PHP payload', re.compile(rb"\b(?:base64_decode|gzinflate|str_rot13)\s*\([^)]{0,300}\).*?\b(?:eval|assert)\s*\(", re.I | re.S)),
)
SOURCE_EXT = {'.php', '.phtml', '.php3', '.php4', '.php5', '.php7', '.php8', '.phar', '.xhtml', '.html', '.htm'}
MAX_LOCAL_FILES = 50000
MAX_LOCAL_BYTES = 3_000_000

def audit_local_folder(folder, cancel, emit):
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise ValueError('Folder tidak ditemukan atau tidak dapat dibuka.')
    scanned = 0
    flagged = 0
    skipped = 0
    for current_dir, dirs, files in os.walk(root, followlinks=False):
        if cancel.is_set() or scanned >= MAX_LOCAL_FILES:
            break
        dirs[:] = [d for d in dirs if not (Path(current_dir) / d).is_symlink()]
        for filename in files:
            if cancel.is_set() or scanned >= MAX_LOCAL_FILES:
                break
            path = Path(current_dir) / filename
            if path.is_symlink() or path.suffix.lower() not in SOURCE_EXT:
                continue
            scanned += 1
            try:
                if path.stat().st_size > MAX_LOCAL_BYTES:
                    skipped += 1
                    continue
                data = path.read_bytes()
                matches = [label for label, regex in SUSPICIOUS_RULES if regex.search(data)]
                item = {
                    'path': str(path.relative_to(root)),
                    'status': 'REVIEW' if matches else 'OK',
                    'type': path.suffix.lstrip('.').upper(),
                    'sha256': hashlib.sha256(data).hexdigest(),
                    'reason': ', '.join(matches) if matches else 'Tidak ada indikator dari aturan terbatas',
                }
                if matches:
                    flagged += 1
                emit('result', item)
            except (OSError, PermissionError):
                skipped += 1
            if scanned % 100 == 0:
                emit('status', f'[LOCAL] {scanned} file diperiksa • {flagged} perlu review')
    outcome = 'STOPPED' if cancel.is_set() else 'DONE'
    emit('status', f'[{outcome}] {scanned} file • {flagged} perlu review • {skipped} dilewati')


def open_window(parent, on_back=None):
    win = ctk.CTkToplevel(parent)
    win.title('JKSY • Web Shell / Directory Audit')
    win.geometry('830x675')
    win.minsize(750, 590)
    win.configure(fg_color=BG)
    win.transient(parent)
    state = {'running': False, 'cancel': threading.Event(), 'paths': DEFAULT_PATHS[:], 'results': [], 'closed': False}
    event_queue = queue.Queue()

    heading = ctk.CTkFrame(win, fg_color=PANEL)
    heading.pack(fill='x', padx=14, pady=(12, 8))
    ctk.CTkLabel(heading, text='🌐 JKSY WEB DIRECTORY AUDIT', text_color='#00FF66',
                 font=('Segoe UI', 18, 'bold')).pack(anchor='w', padx=14, pady=(12, 3))
    ctk.CTkLabel(heading, text='Menampilkan semua status HTTP aktual; PHP/XHTML diberi tanda khusus. URL tersembunyi memerlukan akses hosting',
                 text_color='#AAAAAA', font=('Segoe UI', 11)).pack(anchor='w', padx=14, pady=(0, 12))

    settings = ctk.CTkFrame(win, fg_color=PANEL)
    settings.pack(fill='x', padx=14, pady=(0, 8))
    target = ctk.CTkEntry(settings, placeholder_text='Input HTTPS URL atau folder lokal website (sesuai mode)', height=34)
    target.pack(fill='x', padx=12, pady=(12, 8))
    controls = ctk.CTkFrame(settings, fg_color='transparent')
    controls.pack(fill='x', padx=12, pady=(0, 8))
    path_label = ctk.CTkLabel(controls, text=f'Path: {len(state["paths"])} / {MAX_PATHS}', text_color='#A7F3D0')
    path_label.pack(side='left')
    mode = ctk.StringVar(value='None')
    ctk.CTkOptionMenu(controls, variable=mode,
                      values=['None', 'Discovery', 'Cms', 'Deep', 'Manual', 'Audith'],
                      width=105, height=28, fg_color=BLUE,
                      button_color='#143c68', button_hover_color='#245a93',
                      ).pack(side='right', padx=(0, 6))
    confirm = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(settings, variable=confirm, text='Saya mengelola website/folder ini dan berizin memeriksanya.',
                    font=('Segoe UI', 11)).pack(anchor='w', padx=12, pady=(0, 12))

    main = ctk.CTkFrame(win, fg_color='transparent')
    main.pack(fill='both', expand=True, padx=14, pady=(0, 8))
    left = ctk.CTkFrame(main, fg_color=PANEL)
    left.pack(side='left', fill='both', expand=True, padx=(0, 5))
    right = ctk.CTkFrame(main, fg_color=PANEL, width=270)
    right.pack(side='right', fill='both', padx=(5, 0))
    ctk.CTkLabel(left, text='📂 Semua HTTP Results (PHP / XHTML)', text_color='#38BDF8',
                 font=('Segoe UI', 12, 'bold')).pack(anchor='w', padx=10, pady=(8, 4))
    result_box = ctk.CTkTextbox(left, fg_color='#000000', text_color='#00FF66',
                                font=('Consolas', 11), wrap='word')
    result_box.pack(fill='both', expand=True, padx=9, pady=(0, 9))
    ctk.CTkLabel(right, text='📋 Status Hasil', text_color='#38BDF8',
                 font=('Segoe UI', 12, 'bold')).pack(anchor='w', padx=10, pady=(8, 4))
    status_box = ctk.CTkTextbox(right, fg_color='#000000', text_color='#00FF66',
                                font=('Consolas', 10), wrap='word')
    status_box.pack(fill='both', expand=True, padx=9, pady=(0, 9))

    def write(widget, value):
        widget.configure(state='normal')
        widget.insert('end', value + '\n')
        widget.see('end')
        widget.configure(state='disabled')
    write(status_box, '[SYSTEM] Directory Auditor Ready')
    write(status_box, '[STATUS] Menunggu konfigurasi')

    def import_paths():
        if state['running']:
            return
        file = filedialog.askopenfilename(parent=win, title='Import daftar path (TXT)',
                                          filetypes=[('Text Files', '*.txt')])
        if not file:
            return
        try:
            lines = Path(file).read_text(encoding='utf-8-sig').splitlines()
            valid = list(dict.fromkeys(p for line in lines if (p := validate_path(line)) and not p.startswith('#')))
            if not valid:
                raise ValueError('Tidak ada path valid.')
            if len(valid) > MAX_PATHS:
                raise ValueError(f'Maksimal {MAX_PATHS} path untuk satu pemeriksaan.')
            state['paths'] = valid
            path_label.configure(text=f'Path: {len(valid)} / {MAX_PATHS}')
            write(status_box, f'[IMPORT] {len(valid)} path berhasil dimuat')
        except (OSError, UnicodeError, ValueError) as exc:
            messagebox.showerror('Import Path', str(exc), parent=win)

    ctk.CTkButton(controls, text='Import Path', width=105, height=28, fg_color=BLUE,
                  command=import_paths).pack(side='right', padx=(0, 6))
    def choose_folder():
        chosen = filedialog.askdirectory(parent=win, title='Pilih folder root website')
        if chosen:
            target.delete(0, 'end')
            target.insert(0, chosen)
            mode.set('Audith')
    ctk.CTkButton(controls, text='Pilih Folder', width=105, height=28, fg_color=BLUE,
                  command=choose_folder).pack(side='right', padx=(0, 6))

    actions = ctk.CTkFrame(win, fg_color='transparent')
    actions.pack(fill='x', padx=14, pady=(0, 12))

    def finish_run():
        state['running'] = False
        start_btn.configure(state='normal')
        stop_btn.configure(state='disabled')

    def pump():
        if state['closed'] or not win.winfo_exists():
            return
        try:
            while True:
                event, data = event_queue.get_nowait()
                if event == 'result':
                    state['results'].append(data)
                    kind = data.get('type', 'PATH')
                    priority = ' [PHP/XHTML]' if kind in ('PHP', 'PHTML', 'PHP3', 'PHP4', 'PHP5', 'PHP7', 'PHP8', 'XHTML') else ''
                    extra = f" → {data['location']}" if data.get('location') and str(data.get('status')) in ('301', '302', '303', '307', '308') else ''
                    note = f" • {data['reason']}" if data.get('status') == 'REVIEW' or data.get('source') == 'CMS FINGERPRINT' else ''
                    write(result_box, f"[{data['status']}] [{kind}]{priority} {data['path']}{extra}{note}")
                elif event == 'status':
                    write(status_box, data)
                elif event == 'done':
                    finish_run()
        except queue.Empty:
            pass
        win.after(100, pump)

    def start():
        if state['running']:
            return
        if not confirm.get():
            messagebox.showwarning('Permission', 'Konfirmasi izin pemeriksaan terlebih dahulu.', parent=win)
            return
        selected_mode = mode.get()
        if selected_mode == 'None':
            messagebox.showwarning('Pilih Mode', 'Pilih mode scan terlebih dahulu.', parent=win)
            return
        if selected_mode == 'Audith':
            folder_path = target.get().strip()
            if not Path(folder_path).expanduser().is_dir():
                messagebox.showerror('Target', 'Pilih folder website yang ada pada komputer/server.', parent=win)
                return
            origin = folder_path
        else:
            try:
                origin = validate_target(target.get())
            except ValueError as exc:
                messagebox.showerror('Target', str(exc), parent=win)
                return
        state['results'].clear()
        result_box.configure(state='normal')
        result_box.delete('1.0', 'end')
        result_box.configure(state='disabled')
        state['cancel'].clear()
        state['running'] = True
        start_btn.configure(state='disabled')
        stop_btn.configure(state='normal')
        paths_snapshot = state['paths'][:]
        event_queue.put(('status', f'[RUNNING] {selected_mode} pada {origin}'))

        def worker():
            if selected_mode == 'Audith':
                try:
                    audit_local_folder(origin, state['cancel'], lambda event, data: event_queue.put((event, data)))
                except Exception as exc:
                    event_queue.put(('status', '[ERROR] ' + str(exc)))
                finally:
                    event_queue.put(('done', None))
                return
            if selected_mode in ('Discovery', 'Cms', 'Deep'):
                try:
                    emit = lambda event, data: event_queue.put((event, data))
                    if selected_mode == 'Cms':
                        scan_cms(origin, state['cancel'], emit)
                    elif selected_mode == 'Deep':
                        cms_discovery(origin, state['cancel'], emit)
                    else:
                        public_discovery(origin, state['cancel'], emit)
                except Exception as exc:
                    event_queue.put(('status', '[ERROR] ' + str(exc)))
                finally:
                    event_queue.put(('done', None))
                return
            checked = 0
            for path in paths_snapshot:
                if state['cancel'].is_set():
                    break
                url = urljoin(origin, path)
                # Show real HTTP response status; redirects are never followed.
                # GET handles websites that disallow HEAD, without executing scripts locally.
                http_status, mime, _, location = fetch_public(url, method='GET')
                status = str(http_status)
                checked += 1
                event_queue.put(('result', {'path': path, 'status': status, 'type': file_type(path, mime), 'content_type': mime, 'location': location}))
                event_queue.put(('status', f'[RUNNING] [CHECK] {checked}/{len(paths_snapshot)} Path'))
                # Conservative rate: maximum one request per second.
                if state['cancel'].wait(1.0):
                    break
            event_queue.put(('status', f'[STOPPED] {checked} path dicek' if state['cancel'].is_set()
                             else f'[DONE] {checked} path diperiksa'))
            event_queue.put(('done', None))

        threading.Thread(target=worker, daemon=True).start()

    def stop():
        state['cancel'].set()
        write(status_box, '[STOP] Menghentikan pemeriksaan...')

    def clear():
        if state['running']:
            messagebox.showwarning('Scan', 'Stop proses sebelum Clear.', parent=win)
            return
        state['results'].clear()
        for box in (result_box, status_box):
            box.configure(state='normal')
            box.delete('1.0', 'end')
            box.configure(state='disabled')
        write(status_box, '[SYSTEM] Directory Auditor Ready')

    def export():
        if not state['results']:
            messagebox.showwarning('Export', 'Belum ada hasil pemeriksaan.', parent=win)
            return
        path = filedialog.asksaveasfilename(parent=win, defaultextension='.txt',
                                             initialfile='JKSY_Directory_Audit.txt',
                                             filetypes=[('Text Files', '*.txt')])
        if path:
            try:
                lines = ['STATUS\tTYPE\tPATH\tCONTENT_TYPE\tREDIRECT\tNOTE\tSHA256'] + [f"{v['status']}\t{v.get('type', '')}\t{v['path']}\t{v.get('content_type', '')}\t{v.get('location', '')}\t{v.get('reason', '')}\t{v.get('sha256', '')}" for v in state['results']]
                Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')
                write(status_box, f'[SAVE SUCCESS] {Path(path).name}')
            except OSError as exc:
                messagebox.showerror('Export', str(exc), parent=win)

    def close():
        state['closed'] = True
        state['cancel'].set()
        win.destroy()
        if on_back:
            on_back()
        elif parent.winfo_exists():
            parent.deiconify()
            parent.lift()

    start_btn = ctk.CTkButton(actions, text='Scan', command=start, width=90, fg_color=GREEN)
    start_btn.pack(side='left', padx=(0, 6))
    stop_btn = ctk.CTkButton(actions, text='Stop', command=stop, width=90,
                             fg_color='#991B1B', state='disabled')
    stop_btn.pack(side='left', padx=(0, 6))
    ctk.CTkButton(actions, text='Clear', command=clear, width=90,
                  fg_color='#555555').pack(side='left', padx=(0, 6))
    ctk.CTkButton(actions, text='Export', command=export, width=90,
                  fg_color=BLUE).pack(side='left')
    ctk.CTkButton(actions, text='← Kembali', command=close, width=120,
                  fg_color='#991B1B').pack(side='right')
    win.protocol('WM_DELETE_WINDOW', close)
    win.after(100, pump)
    return win


class NoRedirect(__import__('urllib.request', fromlist=['HTTPRedirectHandler']).HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


if __name__ == '__main__':
    print('ACCESS DENIED: Jalankan Web Shell melalui aplikasi.py')
    raise SystemExit(1)
