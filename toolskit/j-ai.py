"""JKSY J Ai: browser-style multimodal chat. Imported by aplikasi.py."""
import base64
import io
import json
import mimetypes
import os
import queue
import threading
import urllib.error
import urllib.request
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

BG = '#101113'
PANEL = '#1b1d20'
SURFACE = '#24272b'
GREEN = '#22c55e'
BLUE = '#20558e'
MAX_UPLOAD = 12 * 1024 * 1024
AI_MODELS = {
    'J Ai': {'provider': 'gemini', 'model': 'gemini-3.8-flash', 'env': 'GEMINI_API_KEY'},
    'Open Ai': {'provider': 'openai', 'model': 'gpt-4.1-mini', 'env': 'OPENAI_API_KEY'},
}
IMAGE_MODEL = os.environ.get('JAI_GEMINI_IMAGE_MODEL', 'gemini-2.5-flash-image')


def _http_json(url, headers, payload):
    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                                 headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)


def _make_part(attachment):
    mime = attachment['mime']
    if mime.startswith('image/') or mime == 'application/pdf':
        return {'inline_data': {'mime_type': mime, 'data': attachment['base64']}}
    if attachment.get('text') is not None:
        return {'text': '[File ' + attachment['name'] + ']\n' + attachment['text']}
    return None


def request_ai(selection, history, prompt, attachment, key, edit_image=False):
    cfg = AI_MODELS[selection]
    if cfg['provider'] == 'gemini':
        model = IMAGE_MODEL if edit_image else cfg['model']
        endpoint = 'https://generativelanguage.googleapis.com/v1beta/models/' + model + ':generateContent'
        contents = [{'role': 'model' if m['role'] == 'assistant' else 'user',
                     'parts': [{'text': m['content']}]} for m in history]
        parts = [{'text': prompt or 'Jelaskan lampiran ini.'}]
        if attachment:
            part = _make_part(attachment)
            if part:
                parts.append(part)
        contents.append({'role': 'user', 'parts': parts})
        payload = {'contents': contents}
        if edit_image:
            payload['generationConfig'] = {'responseModalities': ['TEXT', 'IMAGE']}
        data = _http_json(endpoint, {'Content-Type': 'application/json', 'x-goog-api-key': key}, payload)
        out_text, pictures = [], []
        for candidate in data.get('candidates', []):
            for p in candidate.get('content', {}).get('parts', []):
                if p.get('text'):
                    out_text.append(p['text'])
                blob = p.get('inlineData') or p.get('inline_data') or {}
                if blob.get('data') and blob.get('mimeType', blob.get('mime_type', '')).startswith('image/'):
                    pictures.append((base64.b64decode(blob['data']), blob.get('mimeType', blob.get('mime_type', 'image/png'))))
        return '\n'.join(out_text).strip(), pictures

    content = [{'type': 'input_text', 'text': prompt or 'Jelaskan lampiran ini.'}]
    if attachment:
        mime = attachment['mime']
        data_uri = 'data:' + mime + ';base64,' + attachment['base64']
        if mime.startswith('image/'):
            content.append({'type': 'input_image', 'image_url': data_uri})
        elif mime == 'application/pdf':
            content.append({'type': 'input_file', 'filename': attachment['name'], 'file_data': data_uri})
        elif attachment.get('text') is not None:
            content[0]['text'] += '\n\n[File: ' + attachment['name'] + ']\n' + attachment['text']
    input_messages = [{'role': m['role'], 'content': m['content']} for m in history]
    input_messages.append({'role': 'user', 'content': content})
    data = _http_json('https://api.openai.com/v1/responses',
                      {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key},
                      {'model': cfg['model'], 'input': input_messages, 'store': False})
    texts = [c.get('text', '') for item in data.get('output', []) if item.get('type') == 'message'
             for c in item.get('content', []) if c.get('type') == 'output_text']
    return '\n'.join(texts).strip(), []


def read_attachment(path):
    p = Path(path)
    if p.stat().st_size > MAX_UPLOAD:
        raise ValueError('Maksimal ukuran upload 12 MB per file.')
    raw = p.read_bytes()
    mime = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
    text = None
    if mime.startswith('text/') or p.suffix.lower() in ('.json', '.py', '.js', '.ts', '.md', '.csv', '.yaml', '.yml', '.xml', '.log'):
        text = raw.decode('utf-8', errors='replace')[:60000]
    elif not (mime.startswith('image/') or mime == 'application/pdf'):
        # File can be selected, but arbitrary binary formats cannot be understood by these APIs.
        text = None
    return {'name': p.name, 'mime': mime, 'base64': base64.b64encode(raw).decode('ascii'),
            'text': text, 'size': len(raw), 'path': str(p)}


def open_window(parent):
    window = ctk.CTkToplevel(parent)
    window.title('JKSY • J Ai')
    window.geometry('910x720')
    window.minsize(730, 540)
    window.configure(fg_color=BG)
    window.transient(parent)
    state = {'closed': False, 'busy': False, 'history': [], 'attachment': None,
             'results': [], 'manual_keys': {}}
    pending = queue.Queue()
    preview_images = []  # Retain Tk image references.

    header = ctk.CTkFrame(window, fg_color=PANEL, corner_radius=12)
    header.pack(fill='x', padx=14, pady=(12, 8))
    ctk.CTkLabel(header, text='✦ J Ai  |  JKSY AI ASSISTANT', text_color='#00ff66',
                 font=('Segoe UI', 19, 'bold')).pack(anchor='w', padx=16, pady=(10, 2))
    ctk.CTkLabel(header, text='Chat, analisis file, dan preview gambar', text_color='#a6acb3',
                 font=('Segoe UI', 11)).pack(anchor='w', padx=16, pady=(0, 10))

    conversation = ctk.CTkScrollableFrame(window, fg_color='#111214', corner_radius=10)
    conversation.pack(fill='both', expand=True, padx=14, pady=(0, 5))
    status = ctk.CTkLabel(window, text='READY', text_color='#a6acb3', font=('Segoe UI', 10))
    status.pack(fill='x', padx=14)

    def show_image(parent_frame, image_bytes):
        try:
            pil = Image.open(io.BytesIO(image_bytes))
            pil.load()
            w, h = pil.size
            factor = min(420 / max(w, 1), 270 / max(h, 1), 1)
            img = ctk.CTkImage(light_image=pil, dark_image=pil,
                               size=(max(1, int(w * factor)), max(1, int(h * factor))))
            preview_images.append(img)
            ctk.CTkLabel(parent_frame, text='', image=img).pack(anchor='w', pady=(3, 3))
        except Exception:
            ctk.CTkLabel(parent_frame, text='Preview gambar tidak tersedia', text_color='#eab308').pack(anchor='w')

    def bubble(who, txt, pictures=None):
        if state['closed']:
            return
        is_user = who == 'You'
        row = ctk.CTkFrame(conversation, fg_color='transparent')
        row.pack(fill='x', padx=8, pady=3)
        card = ctk.CTkFrame(row, fg_color='#20352b' if is_user else SURFACE, corner_radius=10)
        card.pack(side='left', padx=4)
        title_color = '#7ee2a0' if is_user else '#6ab5ff'
        ctk.CTkLabel(card, text=who, text_color=title_color,
                     font=('Segoe UI', 11, 'bold')).pack(anchor='w', padx=12, pady=(8, 0))
        if txt:
            ctk.CTkLabel(card, text=txt, text_color='#eeeeee', wraplength=610,
                         justify='left', font=('Segoe UI', 12)).pack(anchor='w', padx=12, pady=(2, 8))
        for bytes_data in pictures or []:
            show_image(card, bytes_data)
        def scroll_bottom():
            if not state['closed'] and conversation.winfo_exists():
                conversation._parent_canvas.yview_moveto(1.0)
        window.after(60, scroll_bottom)

    bubble('J Ai', 'Siap. Ketik pesan atau upload file untuk mulai.')

    input_row = ctk.CTkFrame(window, fg_color='transparent')
    input_row.pack(fill='x', padx=14, pady=(6, 5))
    message = ctk.CTkEntry(input_row, height=39, fg_color=SURFACE,
                           placeholder_text='Ketik pesan... (Enter untuk kirim)', font=('Segoe UI', 12))
    message.pack(side='left', expand=True, fill='x', padx=(0, 7))

    file_note = ctk.CTkLabel(window, text='', text_color='#9ca3af', anchor='w', font=('Segoe UI', 10))
    file_note.pack(fill='x', padx=20, pady=(0, 3))

    toolbar = ctk.CTkFrame(window, fg_color=PANEL, corner_radius=9)
    toolbar.pack(fill='x', padx=14, pady=(0, 7))
    model = ctk.StringVar(value='J Ai')

    def model_change(value):
        if state['busy']:
            return
        state['history'].clear()
        model.set(value)
        bubble('J Ai', 'Model ' + value + ' dipilih. Percakapan baru.')

    model_btn = ctk.CTkOptionMenu(toolbar, variable=model, values=list(AI_MODELS), command=model_change,
                                  width=118, height=32, fg_color=BLUE, button_color='#164472')
    model_btn.pack(side='left', padx=(10, 5), pady=8)

    def upload():
        path = filedialog.askopenfilename(parent=window, title='Upload File', filetypes=[('All files', '*.*')])
        if not path:
            return
        try:
            attachment = read_attachment(path)
        except Exception as exc:
            messagebox.showerror('Upload gagal', str(exc), parent=window)
            return
        state['attachment'] = attachment
        file_note.configure(text='Lampiran: ' + attachment['name'] + '  •  ' + str(attachment['size'] // 1024) + ' KB')
        if attachment['mime'].startswith('image/'):
            bubble('You', 'Preview upload: ' + attachment['name'], [Path(path).read_bytes()])
        elif attachment.get('text') is None and attachment['mime'] != 'application/pdf':
            bubble('J Ai', 'File dipilih, tetapi format biner ini belum dapat dianalisis oleh model. ' 
                   'Gunakan gambar, PDF, atau file teks.')
        message.focus_set()

    def api_dialog():
        dialog = ctk.CTkToplevel(window)
        dialog.title('J Ai • API Key')
        dialog.geometry('440x215')
        dialog.transient(window)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text='API Key untuk ' + model.get(), font=('Segoe UI', 14, 'bold')).pack(pady=(18, 8))
        entry = ctk.CTkEntry(dialog, width=390, height=36, show='●', placeholder_text='Masukkan API Key')
        entry.pack(pady=5)
        ctk.CTkLabel(dialog, text='Key manual hanya disimpan di memori selama J Ai terbuka.',
                     text_color='#aaaaaa', font=('Segoe UI', 10)).pack(pady=5)
        def store():
            value = entry.get().strip()
            if value:
                state['manual_keys'][model.get()] = value
                status.configure(text='API manual aktif • ' + model.get())
            dialog.destroy()
        ctk.CTkButton(dialog, text='Save', command=store, fg_color=GREEN, text_color='#000000').pack(pady=6)

    def download():
        if not state['results']:
            messagebox.showinfo('Download', 'Belum ada jawaban AI untuk disimpan.', parent=window)
            return
        last = state['results'][-1]
        if last['images']:
            data, mime = last['images'][-1]
            ext = '.png' if 'png' in mime else '.jpg' if 'jpeg' in mime else '.webp'
            dest = filedialog.asksaveasfilename(parent=window, defaultextension=ext,
                                                initialfile='jai-image' + ext,
                                                filetypes=[('Image', '*' + ext), ('All files', '*.*')])
            if dest:
                Path(dest).write_bytes(data)
                status.configure(text='SAVED • ' + Path(dest).name)
        else:
            dest = filedialog.asksaveasfilename(parent=window, defaultextension='.txt',
                                                initialfile='jai-response.txt', filetypes=[('Text', '*.txt')])
            if dest:
                Path(dest).write_text(last['text'], encoding='utf-8')
                status.configure(text='SAVED • ' + Path(dest).name)

    def send(event=None):
        if state['busy']:
            return 'break'
        prompt = message.get().strip()
        attachment = state['attachment']
        if not prompt and attachment is None:
            return 'break'
        if attachment and attachment['text'] is None and not attachment['mime'].startswith('image/') and attachment['mime'] != 'application/pdf':
            messagebox.showwarning('File tidak didukung', 'Format file ini belum dapat dikirim ke AI.', parent=window)
            return 'break'
        selection = model.get()
        cfg = AI_MODELS[selection]
        key = state['manual_keys'].get(selection) or os.environ.get(cfg['env'], '').strip()
        if not key:
            messagebox.showwarning('API belum tersedia', 'Klik API untuk memasukkan key ' + selection + '.', parent=window)
            return 'break'
        # Image edits are available through an explicitly requested command on Gemini.
        edit_image = bool(attachment and attachment['mime'].startswith('image/') and
                          selection == 'J Ai' and any(word in prompt.lower() for word in ('edit', 'ubah', 'hapus', 'tambahkan', 'ganti', 'remove', 'replace', 'generate')))
        state['busy'] = True
        send_btn.configure(state='disabled')
        status.configure(text='RUNNING • Menunggu AI...')
        bubble('You', prompt or 'Analisis file: ' + attachment['name'])
        snapshot = list(state['history'])
        state['attachment'] = None
        file_note.configure(text='')
        message.delete(0, 'end')

        def worker():
            try:
                answer, pictures = request_ai(selection, snapshot, prompt, attachment, key, edit_image)
                pending.put(('ok', (answer, pictures, prompt)))
            except urllib.error.HTTPError as exc:
                try:
                    details = json.loads(exc.read().decode('utf-8', errors='replace'))
                    description = details.get('error', {}).get('message', str(exc))
                except Exception:
                    description = str(exc)
                pending.put(('err', description))
            except Exception as exc:
                pending.put(('err', str(exc)))
        threading.Thread(target=worker, daemon=True).start()
        return 'break'

    send_btn = ctk.CTkButton(input_row, text='Send', width=100, height=39,
                             fg_color='#2b8a3e', command=send)
    send_btn.pack(side='right')
    message.bind('<Return>', send)

    def pump():
        if state['closed']:
            return
        try:
            while True:
                kind, result = pending.get_nowait()
                if kind == 'ok':
                    answer, pictures, prompt = result
                    state['history'].append({'role': 'user', 'content': prompt or 'Lihat file.'})
                    state['history'].append({'role': 'assistant', 'content': answer or 'Gambar berhasil diproses.'})
                    state['results'].append({'text': answer, 'images': pictures})
                    bubble('J Ai', answer or ('Gambar selesai dibuat.' if pictures else 'Tidak ada respons teks.'),
                           [data for data, _ in pictures])
                    status.configure(text='READY • Hasil tersedia untuk Download')
                else:
                    bubble('J Ai', 'ERROR: ' + str(result))
                    status.configure(text='ERROR • Cek model, API, atau format lampiran')
                state['busy'] = False
                send_btn.configure(state='normal')
        except queue.Empty:
            pass
        window.after(100, pump)

    def clear():
        if state['busy']:
            return
        state['history'].clear()
        state['results'].clear()
        state['attachment'] = None
        file_note.configure(text='')
        for child in conversation.winfo_children():
            child.destroy()
        bubble('J Ai', 'Percakapan baru siap.')

    def close():
        state['closed'] = True
        state['manual_keys'].clear()
        window.destroy()
        if parent.winfo_exists():
            parent.deiconify()
            parent.lift()

    for label, fn in [('Upload', upload), ('Download', download), ('API', api_dialog)]:
        ctk.CTkButton(toolbar, text=label, width=92, height=32, fg_color=BLUE,
                      command=fn).pack(side='left', padx=4, pady=8)
    actions = ctk.CTkFrame(window, fg_color='transparent')
    actions.pack(fill='x', padx=14, pady=(0, 10))
    ctk.CTkButton(actions, text='New Chat', width=110, fg_color=BLUE, command=clear).pack(side='left', padx=(0, 8))
    ctk.CTkButton(actions, text='Clear', width=88, fg_color='#555555', command=clear).pack(side='left')
    ctk.CTkButton(actions, text='← Kembali', width=130, fg_color='#991b1b', command=close).pack(side='right')
    window.protocol('WM_DELETE_WINDOW', close)
    window.after(100, pump)
    message.focus_set()
    return window


if __name__ == '__main__':
    print('ACCESS DENIED: Buka J Ai melalui aplikasi.py.')
    raise SystemExit(1)
