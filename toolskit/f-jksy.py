import threading
import tkinter as tk
from tkinter import messagebox, filedialog
import socket
import requests
import platform
import psutil
import time
import random

global_results = []
global_queue = []
stop_flag = False
pause_flag = False
timer_running = False

def append_log(text_widget, content):
    """Menambahkan teks ke widget log dan otomatis scroll ke bawah."""
    text_widget.configure(state="normal")
    text_widget.insert("end", content)
    text_widget.see("end")
    text_widget.configure(state="disabled")

def get_system_info():
    """Mengambil informasi OS, Prosesor, dan RAM perangkat secara aman."""
    try:
        os_name = f"{platform.system()} {platform.release()}"
        processor = platform.processor()
        if not processor:
            processor = "CPU Intel/AMD"
        
        if platform.system() == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0]
                if cpu_name:
                    processor = cpu_name.strip()
            except:
                pass
                
        ram_gb = round(psutil.virtual_memory().total / (1024.0 ** 3), 1)
        return f"{os_name}", f"{processor}", f"{ram_gb} GB"
    except Exception:
        return platform.system(), "Standard CPU", "8.0 GB"

def check_ping_ms():
    """Mengukur latensi koneksi internet (MS) ke server publik 1.1.1.1."""
    try:
        start = time.time()
        socket.setdefaulttimeout(1)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("1.1.1.1", 53))
        end = time.time()
        ms = int((end - start) * 1000)
        return f"{ms} ms"
    except Exception:
        return "N/A (Offline)"

def update_info_panel(lbl_domains, lbl_time, lbl_ms, scanned_count, elapsed_seconds):
    """Memperbarui informasi di box kanan secara dinamis."""
    try:
        lbl_domains.config(text=str(scanned_count))
        mins, secs = divmod(elapsed_seconds, 60)
        lbl_time.config(text=f"{int(mins):02d}:{int(secs):02d}")
        lbl_ms.config(text=check_ping_ms())
    except Exception:
        pass

def check_domain(domain, text_widget, root_domains):
    """Mengecek domain dengan socket TCP super cepat & timeout sangat singkat (0.35 detik)."""
    try:
        socket.setdefaulttimeout(0.35)
        ip = socket.gethostbyname(domain)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, 80))
        s.close()
        
        if domain not in root_domains:
            root_domains.add(domain)
            append_log(text_widget, f"[+] Ditemukan: {domain}\n")
    except Exception:
        pass

def extract_root_domain(subdomain, tld):
    """Mengekstrak domain utama saja dari subdomain (Mode CRT.SH)."""
    clean_tld = tld.strip('.').lower()
    clean_sub = subdomain.strip().lower()
    
    if '@' in clean_sub or not clean_sub.endswith(clean_tld):
        return None
        
    tld_parts = clean_tld.split('.')
    tld_len = len(tld_parts)
    
    sub_parts = clean_sub.split('.')
    if len(sub_parts) <= tld_len:
        return None
        
    root_parts = sub_parts[-(tld_len + 1):]
    return '.'.join(root_parts)

def generate_prefixes():
    """Menghasilkan kombinasi prefiks domain super masif dengan variasi kata yang kaya."""
    prefixes = set()
    letters = "abcdefghijklmnopqrstuvwxyz"
    vowels = "aeiou"
    consonants = "bcdfghjklmnpqrstvwxyz"
    
    for l in letters:
        prefixes.add(l)
        for l2 in letters:
            prefixes.add(f"{l}{l2}")
            for l3 in letters:
                prefixes.add(f"{l}{l2}{l3}")
                
    for c in consonants:
        for v in vowels:
            for c2 in consonants:
                prefixes.add(f"{c}{v}{c2}")
                for v2 in vowels:
                    prefixes.add(f"{c}{v}{c2}{v2}")

    numbers = [
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
        "01", "02", "03", "04", "05", "06", "07", "08", "09",
        "10", "11", "12", "15", "20", "25", "30", "50", "99",
        "88", "168", "365", "247", "123", "777", "999",
        "2024", "2025", "2026", "2027", "2028", "id", "pro", "shop", "net", "vip"
    ]
    for num in numbers:
        prefixes.add(num)

    base_words = [
        "pusat", "toko", "rumah", "sukses", "berkah", "global", "prima", 
        "mitra", "sumber", "karya", "utama", "mandiri", "abadi", "sejahtera",
        "digital", "solusi", "cipta", "kreatif", "media", "portal", "nusantara",
        "bisnis", "sistem", "anugerah", "bintang", "sentral", "online", "shop", 
        "store", "market", "group", "indonesia", "terpercaya", "terbaik", 
        "express", "kilat", "jaya", "makmur", "teknologi", "official", "pro",
        "plus", "spot", "zona", "gacor", "slot", "crypto", "dompet", "super",
        "mega", "finansial", "investasi", "properti", "kesehatan", "wisata",
        "kuliner", "fashion", "teknik", "logistik", "artha", "dana", "pay",
        "cash", "wallet", "bank", "kredit", "modal", "aura", "cahaya", "sakti",
        "indah", "lestari", "buana", "alam", "sari", "raya", "perdana", "niaga",
        "net", "web", "link", "connect", "hub", "station", "cloud", "data",
        "smart", "fast", "quick", "easy", "auto", "bot", "ai", "cyber",
        "secure", "safe", "shield", "trust", "alpha", "prime", "top", "best",
        "next", "vips", "hoki", "win", "play", "game", "bet", "sport", "bola",
        "live", "tv", "stream", "blog", "news", "info", "code", "dev", "lab",
        "studio", "factory", "works", "craft", "build", "design", "art",
        "style", "food", "cafe", "resto", "fresh", "green", "bio", "eco",
        "health", "care", "fit", "gym", "spa", "beauty", "travel", "tour",
        "pesona", "bahagia", "sentosa", "gemilang", "inspirasi", "karsa", 
        "andalan", "berdikari", "pioner", "inovasi", "visioner", "strategi"
    ]
    
    for w in base_words:
        if 1 <= len(w) <= 40:
            prefixes.add(w)
            for num in ["88", "99", "24", "id", "pro", "shop", "net", "vip", "go", "max"]:
                comb_num = f"{w}{num}"
                if len(comb_num) <= 40:
                    prefixes.add(comb_num)

    pool = base_words[:80]
    for i in range(len(pool)):
        for j in range(len(pool)):
            if i != j:
                combo2 = f"{pool[i]}{pool[j]}"
                if 4 <= len(combo2) <= 35:
                    prefixes.add(combo2)

    subset_pool = base_words[:40]
    for w1 in subset_pool:
        for w2 in subset_pool[:25]:
            p2 = f"{w1}{w2}"
            if len(p2) <= 30:
                prefixes.add(p2)
                for w3 in subset_pool[:15]:
                    p3 = f"{p2}{w3}"
                    if len(p3) <= 40:
                        prefixes.add(p3)
                        for w4 in subset_pool[:8]:
                            p4 = f"{p3}{w4}"
                            if len(p4) <= 48:
                                prefixes.add(p4)

    return list(prefixes)

def scan_crt_sh(tld, text_widget, btn_search, btn_pause_resume, btn_clear, btn_save, lbl_domains, lbl_time, lbl_ms):
    global global_results, stop_flag, pause_flag, timer_running
    
    search_tld = '.' + tld if not tld.startswith('.') else tld
    clean_tld = tld.lstrip('.')
    
    # KODE BARU (Kompatibel dengan CustomTkinter):
    text_widget.configure(state="normal")
    text_widget.delete("0.0", "end")
    text_widget.configure(state="disabled")
    
    append_log(text_widget, f"[*] Memulai pencarian via CRT.SH untuk TLD: .{clean_tld}\n")
    append_log(text_widget, "[*] Mengirim permintaan ke crt.sh (harap tunggu)...\n\n")
    
    root_domains = set(global_results)
    url = f"https://crt.sh/?q=%{search_tld}&output=json"
    
    start_t = time.time()
    timer_running = True
    
    def background_timer():
        while timer_running:
            if not pause_flag:
                elapsed = int(time.time() - start_t)
                update_info_panel(lbl_domains, lbl_time, lbl_ms, len(root_domains), elapsed)
            time.sleep(1)
            
    t_timer = threading.Thread(target=background_timer, daemon=True)
    t_timer.start()
    
    try:
        response = requests.get(url, timeout=45)
        if response.status_code == 200:
            try:
                data = response.json()
            except ValueError:
                append_log(text_widget, "[!] Error: Format respons dari server bukan JSON yang valid.\n")
                return

            append_log(text_widget, "[+] Data diterima dari CRT.SH. Menyaring domain...\n")
            append_log(text_widget, "-" * 50 + "\n")
            
            for entry in data:
                while pause_flag and not stop_flag:
                    time.sleep(0.5)
                if stop_flag:
                    break
                    
                name_value = entry.get('name_value', '')
                for sub in name_value.split('\n'):
                    sub = sub.strip().lower()
                    if '*' not in sub:
                        root_dom = extract_root_domain(sub, clean_tld)
                        if root_dom and root_dom not in root_domains:
                            root_domains.add(root_dom)
                            append_log(text_widget, f"[+] Ditemukan: {root_dom}\n")
        else:
            append_log(text_widget, f"[!] Server CRT.SH merespons dengan status code: {response.status_code}\n")
            
    except requests.exceptions.Timeout:
        append_log(text_widget, "[!] Error: Koneksi ke CRT.SH Timeout. Server sedang sibuk.\n")
    except Exception as e:
        append_log(text_widget, f"[!] Terjadi kesalahan: {e}\n")
    finally:
        timer_running = False
        global_results = sorted(list(root_domains))
        append_log(text_widget, "-" * 50 + "\n")
        append_log(text_widget, f"[+] Selesai! Total unik domain bersih ditemukan: {len(global_results)}\n")
        update_info_panel(lbl_domains, lbl_time, lbl_ms, len(global_results), int(time.time() - start_t))
        
        # Pastikan menggunakan .configure() di sini:
        btn_search.configure(state="normal", fg_color="#10B981", text="Scan")
        btn_pause_resume.configure(state="disabled", fg_color="#334155", text="Pause")
        if len(global_results) > 0:
            btn_save.configure(state="normal", fg_color="#3B82F6")

def search_by_tld(tld_input, mode_var, tld_mode_var, text_widget, btn_search, btn_pause_resume, btn_clear, btn_save, lbl_domains, lbl_time, lbl_ms):
    global global_results, global_queue, stop_flag, pause_flag, timer_running
    
    mode_scanner = mode_var.get()
    tld_mode_val = tld_mode_var.get()
    
    if mode_scanner == "NONE":
        messagebox.showwarning("Peringatan", "Silakan pilih mode scanner (AUTO atau CRT.SH) terlebih dahulu!")
        btn_search.configure(state="normal", fg_color="#2b8a3e", text="Scan")
        btn_pause_resume.configure(state="disabled", fg_color="#495057", text="Pause")
        return

    all_global_regional_tlds = [
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
    
    if tld_mode_val == "Random":
        formatted_tld = random.choice(all_global_regional_tlds)
    elif tld_mode_val == "Manual":
        tld = tld_input.strip().lower()
        if not tld:
            messagebox.showwarning("Peringatan", "Silakan masukkan ekstensi TLD terlebih dahulu karena mode diset ke Manual!")
            btn_search.configure(state="normal", fg_color="#2b8a3e", text="Scan")
            btn_pause_resume.configure(state="disabled", fg_color="#495057", text="Pause")
            return
        formatted_tld = '.' + tld if not tld.startswith('.') else tld
    else:
        tld = tld_input.strip().lower()
        if tld:
            formatted_tld = '.' + tld if not tld.startswith('.') else tld
        else:
            messagebox.showwarning("Peringatan", "Silakan masukkan TLD terlebih dahulu atau pilih mode TLD (Manual/Random)!")
            btn_search.configure(state="normal", fg_color="#2b8a3e", text="Scan")
            btn_pause_resume.configure(state="disabled", fg_color="#495057", text="Pause")
            return

    if mode_scanner == "CRT.SH":
        scan_crt_sh(formatted_tld.lstrip('.'), text_widget, btn_search, btn_pause_resume, btn_clear, btn_save, lbl_domains, lbl_time, lbl_ms)
        return
    
    if not global_queue:
        text_widget.configure(state="normal")
        text_widget.delete("0.0", "end")
        text_widget.configure(state="disabled")
        
        append_log(text_widget, f"[*] Memulai FULL SCAN (AUTO - Mode: {tld_mode_val}) untuk TLD: {formatted_tld}\n")
        append_log(text_widget, "[*] Menghasilkan dan memverifikasi kombinasi domain aktif...\n\n")
        global_queue = generate_prefixes()
    else:
        append_log(text_widget, f"\n[*] Melanjutkan pemindaian untuk TLD: {formatted_tld} (Sisa antrean: {len(global_queue)})\n")
    
    root_domains = set(global_results)
    start_t = time.time()
    timer_running = True
    
    def background_timer():
        while timer_running:
            if not pause_flag:
                elapsed = int(time.time() - start_t)
                update_info_panel(lbl_domains, lbl_time, lbl_ms, len(root_domains), elapsed)
            time.sleep(1)
            
    t_timer = threading.Thread(target=background_timer, daemon=True)
    t_timer.start()
    
    # DITINGKATKAN LAGI: Kapasitas batch threads dinaikkan menjadi 800 sekaligus secara agresif
    while global_queue and not stop_flag:
        # Pengecekan pause wajib berada di dalam loop ini agar thread merespons saat dipause
        while pause_flag and not stop_flag:
            time.sleep(0.5)
        if stop_flag:
            break

        batch = []
        for _ in range(min(800, len(global_queue))):
            if global_queue:
                batch.append(global_queue.pop(0))
        
        # ... sisa proses thread scan ...
                
        threads = []
        for prefix in batch:
            if stop_flag:
                global_queue = batch + global_queue
                break
            
            current_tld = formatted_tld
            if tld_mode_val == "Random":
                current_tld = random.choice(all_global_regional_tlds)
                
            domain = f"{prefix}{current_tld}"
            t = threading.Thread(target=check_domain, args=(domain, text_widget, root_domains))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        global_results = sorted(list(root_domains))
        
    timer_running = False
    elapsed_total = int(time.time() - start_t)
    
    if stop_flag:
        append_log(text_widget, "\n[!] Pemindaian dihentikan sementara.\n")
        btn_search.configure(state="normal", fg_color="#10B981", text="Scan")
        btn_pause_resume.configure(state="disabled", fg_color="#334155", text="Pause")
    else:
        append_log(text_widget, "-" * 50 + "\n")
        append_log(text_widget, f"[+] Selesai! Total unik domain aktif ditemukan: {len(global_results)}\n")
        btn_search.configure(state="normal", fg_color="#10B981", text="Scan")
        btn_pause_resume.configure(state="disabled", fg_color="#334155", text="Pause")
        
    update_info_panel(lbl_domains, lbl_time, lbl_ms, len(global_results), elapsed_total)
    if len(global_results) > 0:
        btn_save.configure(state="normal", fg_color="#3B82F6")

def start_search(entry_tld, mode_var, tld_mode_var, text_widget, btn_search, btn_pause_resume, btn_clear, btn_save, lbl_domains, lbl_time, lbl_ms):
    global stop_flag, pause_flag
    stop_flag = False
    pause_flag = False
    
    btn_search.configure(state="disabled", fg_color="#065F46")
    btn_pause_resume.configure(state="normal", fg_color="#D97706", text="Pause")  # <-- Pastikan state="normal"
    btn_save.configure(state="disabled", fg_color="#1E3A8A")
    
    tld_input = entry_tld.get().strip()
    threading.Thread(target=search_by_tld, args=(tld_input, mode_var, tld_mode_var, text_widget, btn_search, btn_pause_resume, btn_clear, btn_save, lbl_domains, lbl_time, lbl_ms), daemon=True).start()

def toggle_pause_resume(btn_pause_resume):
    global pause_flag
    if not pause_flag:
        pause_flag = True
        btn_pause_resume.configure(text="Resume", fg_color="#2563EB")
    else:
        pause_flag = False
        btn_pause_resume.configure(text="Pause", fg_color="#D97706")

def save_results():
    if not global_results:
        messagebox.showwarning("Peringatan", "Belum ada hasil untuk disimpan!")
        return
        
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
    if file_path:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(global_results) + "\n")
            messagebox.showinfo("Sukses", f"Hasil berhasil disimpan ke:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan file: {e}")

def clear_history(text_widget, entry_tld, btn_search, btn_pause_resume, btn_save, lbl_domains, lbl_time, lbl_ms):
    global global_results, global_queue, stop_flag, pause_flag, timer_running
    stop_flag = True
    pause_flag = False
    timer_running = False
    global_results = []
    global_queue = []
    
    text_widget.configure(state="normal")
    text_widget.delete("0.0", "end")
    text_widget.configure(state="disabled")
    
    entry_tld.delete(0, "end")
    
    btn_search.configure(text="Scan", fg_color="#10B981", state="normal")
    btn_pause_resume.configure(text="Pause", fg_color="#334155", state="disabled")
    btn_save.configure(state="disabled", fg_color="#1E3A8A")
    
    lbl_domains.configure(text="0")
    lbl_time.configure(text="00:00")
    lbl_ms.configure(text="0 ms")

def main():
    root = tk.Tk()
    root.title("Domain Finder GUI • Modern Dashboard")
    root.geometry("1000x600")
    root.minsize(800, 520)
    root.config(bg="#090D16")
    
    # Header Control Panel
    frame_top = tk.Frame(root, bg="#0F172A", padx=18, pady=16)
    frame_top.pack(fill=tk.X, padx=12, pady=12)
    
    lbl_tld = tk.Label(frame_top, text="Masukkan Ekstensi TLD (misal: com, id, co.id):", font=("Segoe UI", 10, "bold"), bg="#0F172A", fg="#38BDF8")
    lbl_tld.pack(anchor=tk.W, pady=(0, 8))
    
    frame_input_row = tk.Frame(frame_top, bg="#0F172A")
    frame_input_row.pack(fill=tk.X)
    
    # Ukuran standar yang sama persis untuk semua tombol
    btn_width = 10
    btn_font = ("Segoe UI", 10, "bold")

    # Tombol Aksi Kanan
    btn_save = tk.Button(frame_input_row, text="Save", bg="#1E3A8A", fg="#93C5FD", font=btn_font, 
                         activebackground="#2563EB", activeforeground="white", relief=tk.FLAT, bd=0, 
                         width=btn_width,
                         cursor="hand2", state=tk.DISABLED, disabledforeground="#475569", command=save_results)
    btn_save.pack(side=tk.RIGHT, ipady=6)
    
    btn_clear = tk.Button(frame_input_row, text="Clear", bg="#7F1D1D", fg="#FCA5A5", font=btn_font, 
                          activebackground="#DC2626", activeforeground="white", relief=tk.FLAT, bd=0, 
                          width=btn_width,
                          cursor="hand2", command=lambda: clear_history(text_output, entry_tld, btn_search, btn_pause_resume, btn_save, lbl_domains_val, lbl_time_val, lbl_ms_val))
    btn_clear.pack(side=tk.RIGHT, padx=(0, 10), ipady=6)
    
    btn_pause_resume = tk.Button(frame_input_row, text="Pause", bg="#334155", fg="#94A3B8", font=btn_font, 
                                 activebackground="#475569", activeforeground="white", relief=tk.FLAT, bd=0, 
                                 width=btn_width,
                                 cursor="hand2", state=tk.DISABLED, disabledforeground="#475569", command=lambda: toggle_pause_resume(btn_pause_resume))
    btn_pause_resume.pack(side=tk.RIGHT, padx=(0, 10), ipady=6)
    
    btn_search = tk.Button(frame_input_row, text="Scan", bg="#10B981", fg="white", font=btn_font, 
                           activebackground="#059669", activeforeground="white", relief=tk.FLAT, bd=0, 
                           width=btn_width,
                           cursor="hand2", command=lambda: start_search(entry_tld, mode_var, tld_mode_var, text_output, btn_search, btn_pause_resume, btn_clear, btn_save, lbl_domains_val, lbl_time_val, lbl_ms_val))
    btn_search.pack(side=tk.RIGHT, padx=(0, 10), ipady=6)
    
    # Dropdown Mode Scanner (Kustom tanpa indikator jelek)
    mode_var = tk.StringVar(root)
    mode_var.set("NONE")
    
    menu_mode = tk.Menu(root, tearoff=0, bg="#1E293B", fg="#F8FAFC", font=("Segoe UI", 9))
    menu_mode.add_command(label="NONE", command=lambda: mode_var.set("NONE"))
    menu_mode.add_command(label="AUTO", command=lambda: mode_var.set("AUTO"))
    menu_mode.add_command(label="CRT.SH", command=lambda: mode_var.set("CRT.SH"))
    
    def show_menu_mode(event):
        try:
            menu_mode.tk_popup(event.widget.winfo_rootx(), event.widget.winfo_rooty() + event.widget.winfo_height())
        finally:
            menu_mode.grab_release()

    btn_mode = tk.Button(frame_input_row, textvariable=mode_var, bg="#1E293B", fg="#38BDF8", font=btn_font,
                         activebackground="#334155", activeforeground="white", relief=tk.FLAT, bd=0,
                         width=btn_width, cursor="hand2")
    btn_mode.pack(side=tk.RIGHT, padx=(0, 10), ipady=6)
    btn_mode.bind("<Button-1>", show_menu_mode)

    # Dropdown TLD Mode Kustom
    tld_mode_var = tk.StringVar(root)
    tld_mode_var.set("NONE")
    
    menu_tld = tk.Menu(root, tearoff=0, bg="#1E293B", fg="#F8FAFC", font=("Segoe UI", 9))
    menu_tld.add_command(label="NONE", command=lambda: tld_mode_var.set("NONE"))
    menu_tld.add_command(label="Manual", command=lambda: tld_mode_var.set("Manual"))
    menu_tld.add_command(label="Random", command=lambda: tld_mode_var.set("Random"))
    
    def show_menu_tld(event):
        try:
            menu_tld.tk_popup(event.widget.winfo_rootx(), event.widget.winfo_rooty() + event.widget.winfo_height())
        finally:
            menu_tld.grab_release()

    btn_tld_mode = tk.Button(frame_input_row, textvariable=tld_mode_var, bg="#1E293B", fg="#38BDF8", font=btn_font,
                             activebackground="#334155", activeforeground="white", relief=tk.FLAT, bd=0,
                             width=btn_width, cursor="hand2")
    btn_tld_mode.pack(side=tk.RIGHT, padx=(0, 10), ipady=6)
    btn_tld_mode.bind("<Button-1>", show_menu_tld)
    
    entry_tld = tk.Entry(frame_input_row, width=16, font=("Segoe UI", 12), bg="#1E293B", fg="#F8FAFC", insertbackground="white", relief=tk.FLAT)
    entry_tld.pack(side=tk.LEFT, ipady=8, ipadx=8)
    
    # Body Area (Dua Kolom: Log & Stats Dashboard)
    frame_bottom = tk.Frame(root, bg="#090D16")
    frame_bottom.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
    
    frame_bottom.columnconfigure(0, weight=3)
    frame_bottom.columnconfigure(1, weight=2)
    frame_bottom.rowconfigure(0, weight=1)
    
    # Sisi Kiri: Live Log
    frame_left = tk.Frame(frame_bottom, bg="#0F172A", padx=12, pady=12)
    frame_left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    
    lbl_box1 = tk.Label(frame_left, text="📊 Live Domain Log", font=("Segoe UI", 9, "bold"), bg="#0F172A", fg="#38BDF8")
    lbl_box1.pack(anchor=tk.W, pady=(0, 8))
    
    text_output = tk.Text(frame_left, wrap=tk.WORD, font=("Consolas", 9), 
                          bg="#090D16", fg="#34D399", insertbackground="white", relief=tk.FLAT, padx=6, pady=6)
    text_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    text_output.config(state=tk.DISABLED)
    
    def on_mouse_wheel(event):
        if platform.system() == "Windows":
            text_output.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif platform.system() == "Darwin":
            text_output.yview_scroll(int(-1 * event.delta), "units")
        else:
            if event.num == 4:
                text_output.yview_scroll(-1, "units")
            elif event.num == 5:
                text_output.yview_scroll(1, "units")
        return "break"

    text_output.bind("<MouseWheel>", on_mouse_wheel)
    text_output.bind("<Button-4>", on_mouse_wheel)
    text_output.bind("<Button-5>", on_mouse_wheel)
    
    # Sisi Kanan: System & Stats Cards
    frame_right = tk.Frame(frame_bottom, bg="#0F172A", padx=12, pady=12)
    frame_right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    
    lbl_box2 = tk.Label(frame_right, text="💻 System & Stats Dashboard", font=("Segoe UI", 9, "bold"), bg="#0F172A", fg="#38BDF8")
    lbl_box2.pack(anchor=tk.W, pady=(0, 10))
    
    os_info, cpu_info, ram_info = get_system_info()
    
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
        row_f = tk.Frame(frame_right, bg="#1E293B", padx=8, pady=6)
        row_f.pack(fill=tk.X, pady=3)
        
        lbl_key = tk.Label(row_f, text=label, font=("Segoe UI", 8, "bold"), bg="#1E293B", fg="#94A3B8", width=11, anchor="w")
        lbl_key.pack(side=tk.LEFT)
        
        val_fg = "#34D399" if label not in ["Developer", "Telegram"] else "#F43F5E" if label == "Telegram" else "#38BDF8"
        
        lbl_val = tk.Label(row_f, text=val, font=("Segoe UI", 8, "bold"), bg="#1E293B", fg=val_fg, anchor="w")
        lbl_val.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        if label == "GET DOMAIN":
            global lbl_domains_val
            lbl_domains_val = lbl_val
        elif label == "TIME":
            global lbl_time_val
            lbl_time_val = lbl_val
        elif label == "MS":
            global lbl_ms_val
            lbl_ms_val = lbl_val

    root.mainloop()



# Finder JKSY unified interface: all Tk widget changes happen in GUI thread.
# Semua ekstensi TLD untuk pencarian AUTO/CRT.SH.
ALL_FINDER_TLDS = ('com', 'net', 'org', 'info', 'biz', 'name', 'pro', 'xyz', 'online', 'site', 'tech', 'store', 'shop', 'app', 'dev', 'io', 'co', 'me', 'cc', 'tv', 'ws', 'icu', 'top', 'vip', 'club', 'fun', 'space', 'press', 'news', 'media', 'studio', 'agency', 'expert', 'solutions', 'services', 'systems', 'network', 'global', 'cloud', 'digital', 'finance', 'ventures', 'holdings', 'partners', 'company', 'limited', 'today', 'live', 'life', 'world', 'email', 'link', 'click', 'support', 'center', 'id', 'co.id', 'or.id', 'sch.id', 'ac.id', 'net.id', 'go.id', 'mil.id', 'my.id', 'web.id', 'biz.id', 'desa.id', 'asia', 'sg', 'my', 'ph', 'th', 'vn', 'in', 'jp', 'kr', 'cn', 'hk', 'tw', 'au', 'nz', 'bn', 'kh', 'la', 'mm', 'pk', 'bd', 'lk', 'np', 'mv', 'mn', 'eu', 'uk', 'co.uk', 'org.uk', 'de', 'fr', 'it', 'es', 'nl', 'ru', 'ch', 'se', 'no', 'fi', 'dk', 'pl', 'pt', 'gr', 'ie', 'at', 'be', 'cz', 'hu', 'ro', 'ua', 'us', 'ca', 'mx', 'br', 'ar', 'cl', 'co', 'pe', 've', 'ec', 'bo', 'py', 'uy', 'ae', 'sa', 'qa', 'kw', 'bh', 'om', 'jo', 'lb', 'il', 'tr', 'eg', 'za', 'ng')

def render_jksy_finder(root, on_back=None):
    import customtkinter as ctk
    import queue
    import concurrent.futures
    from datetime import datetime

    global global_results, global_queue, stop_flag, pause_flag, timer_running
    global_results = []
    global_queue = []
    stop_flag = False
    pause_flag = False
    timer_running = False
    ctk.set_appearance_mode("Dark")
    root.title("JKSY Finder • Domain Discovery")
    root.geometry("800x700")
    root.minsize(800, 700)
    root.configure(fg_color="#101114")
    FONT = ("Segoe UI", 11, "bold")
    PANEL = ("#e9ecef", "#1a1a1a")
    GREEN, BLUE = "#2b8a3e", "#1f538d"
    events = queue.Queue()
    state = {"running": False, "paused": False, "closed": False, "started": 0.0,
             "found": set(), "checked": 0, "mode": "NONE", "last_ping": "N/A", "job": 0,
             "pause_since": None, "paused_total": 0.0}
    lock = threading.Lock()
    session_cancel = threading.Event()

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", padx=16, pady=(10, 5))
    ctk.CTkLabel(header, text="⚡ JOKESKY DOMAIN FINDER", font=("Segoe UI", 16, "bold")).pack(side="left")
    ctk.CTkLabel(header, text=" JKSY-FINDER ", font=FONT, fg_color=BLUE,
                 text_color="white", corner_radius=6).pack(side="left", padx=12)

    body = ctk.CTkFrame(root, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=15, pady=(0, 10))
    columns = ctk.CTkFrame(body, fg_color="transparent")
    columns.pack(fill="both", expand=True, pady=(4, 3))
    columns.grid_columnconfigure(0, weight=3, uniform="finder")
    columns.grid_columnconfigure(1, weight=2, uniform="finder")
    columns.grid_rowconfigure(1, weight=1)
    ctk.CTkLabel(columns, text="📂 Domain Target (Live Scan)", font=FONT,
                 text_color="gray").grid(row=0, column=0, sticky="w", pady=(0, 4))
    ctk.CTkLabel(columns, text="📊 Status Hasil", font=FONT,
                 text_color="gray").grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 4))
    text_output = ctk.CTkTextbox(columns, font=("Consolas", 11), fg_color="#000000",
                                  text_color="#00FF66", wrap="word")
    text_output.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
    text_output.configure(state="disabled")
    status_output = ctk.CTkTextbox(columns, font=("Consolas", 11), fg_color="#000000",
                                    text_color="#ffffff", width=270)
    status_output.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
    status_output.insert("end", "[SYSTEM] Finder Ready\n[STATUS] Waiting for configuration\n")
    status_output.configure(state="disabled")

    stats = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=7)
    stats.pack(fill="x", pady=(6, 5))
    lbl_domains_val = ctk.CTkLabel(stats, text="0", text_color="#00FF66", font=FONT)
    lbl_time_val = ctk.CTkLabel(stats, text="00:00", text_color="#00FFFF", font=FONT)
    lbl_ms_val = ctk.CTkLabel(stats, text="Checking...", text_color="#00FFFF", font=FONT)
    for label, widget in (("GET DOMAIN:", lbl_domains_val), ("TIME:", lbl_time_val), ("MS:", lbl_ms_val)):
        group = ctk.CTkFrame(stats, fg_color="transparent")
        group.pack(side="left", expand=True, padx=7, pady=5)
        ctk.CTkLabel(group, text=label, font=("Consolas", 10), text_color="gray").pack(side="left", padx=4)
        widget.pack(side="left")

    lower = ctk.CTkFrame(body, fg_color="transparent")
    lower.pack(fill="x", pady=(5, 5))
    info = ctk.CTkFrame(lower, fg_color=PANEL, corner_radius=8)
    info.pack(side="left", fill="both", expand=True, padx=(0, 6))
    ctk.CTkLabel(info, text="⚙️ System & Hardware", font=FONT).pack(anchor="w", padx=10, pady=(6, 2))
    info_box = ctk.CTkTextbox(info, height=130, fg_color="#000000", text_color="#00FFFF", font=("Consolas", 10))
    info_box.pack(fill="x", padx=8, pady=(0, 7))
    os_info, cpu_info, ram_info = get_system_info()
    info_box.insert("end", f"OS       : {os_info}\nCPU      : {cpu_info[:31]}\nRAM      : {ram_info}\nCREATOR  : JOKESKYLS\nTELEGRAM : @nazisme1930")
    info_box.configure(state="disabled")
    control = ctk.CTkFrame(lower, fg_color=PANEL, corner_radius=8, width=365)
    control.pack(side="right", fill="both", padx=(6, 0))
    control.pack_propagate(False)
    ctk.CTkLabel(control, text="🎯 Filter Output TLD", font=FONT).pack(anchor="w", padx=12, pady=(7, 2))
    entry_tld = ctk.CTkEntry(control, placeholder_text="Manual: com, id, co.id ...", height=30)
    entry_tld.pack(fill="x", padx=12, pady=(0, 6))
    mode_var = ctk.StringVar(value="NONE")
    tld_mode_var = ctk.StringVar(value="NONE")
    mode_row = ctk.CTkFrame(control, fg_color="transparent")
    mode_row.pack(fill="x", padx=12, pady=3)
    ctk.CTkOptionMenu(mode_row, variable=mode_var, values=["NONE", "AUTO", "CRT.SH"],
                      fg_color=BLUE, button_color="#143c68", width=155).pack(side="left")
    ctk.CTkOptionMenu(mode_row, variable=tld_mode_var, values=["NONE", "Manual", "Random", "Semua TLD"],
                      fg_color=BLUE, button_color="#143c68", width=155).pack(side="right")
    ctk.CTkLabel(control, text="Mode scanner       Mode TLD", text_color="gray",
                 font=("Segoe UI", 10)).pack(anchor="w", padx=13, pady=(0, 2))

    actions = ctk.CTkFrame(body, fg_color="transparent")
    actions.pack(fill="x", pady=(5, 0))
    btn_save = ctk.CTkButton(actions, text="💾 Save", width=84, height=29,
                              fg_color=BLUE, state="disabled", font=FONT)
    btn_search = ctk.CTkButton(actions, text="🔍 Scan", width=84, height=29,
                                fg_color=GREEN, font=FONT)
    btn_pause_resume = ctk.CTkButton(actions, text="Pause", width=84, height=29,
                                      fg_color="#495057", state="disabled", font=FONT)
    btn_clear = ctk.CTkButton(actions, text="🗑️ Clear", width=84, height=29,
                               fg_color="#495057", font=FONT)

    status_history = ['[SYSTEM] Finder Ready', '[STATUS] Waiting for configuration']
    status_progress = [None]

    def render_status():
        # Batasi riwayat dan tampilkan progres GET di satu baris yang diperbarui.
        status_output.configure(state='normal')
        status_output.delete('0.0', 'end')
        rows = status_history[-18:]
        if status_progress[0] is not None:
            rows = rows + [status_progress[0]]
        status_output.insert('end', '\n'.join(rows) + '\n')
        status_output.see('end')
        status_output.configure(state='disabled')

    def write(widget, message):
        if state['closed']:
            return
        if widget is status_output:
            # Simpan status penting; progres berjalan tidak dibuat menjadi spam log.
            status_history.append(message)
            render_status()
            return
        widget.configure(state="normal")
        widget.insert("end", message + "\n")
        widget.see("end")
        widget.configure(state="disabled")

    def finish(msg):
        if state['pause_since'] is not None:
            state['paused_total'] += time.monotonic() - state['pause_since']
            state['pause_since'] = None
        state['running'] = False
        state['paused'] = False
        btn_search.configure(state="normal", text="🔍 Scan")
        btn_pause_resume.configure(state="disabled", text="Pause")
        btn_save.configure(state="normal" if state['found'] else "disabled")
        status_progress[0] = None
        write(status_output, msg)

    def process_events():
        if state['closed']:
            return
        try:
            for _ in range(200):
                kind, job, data = events.get_nowait()
                if job != state['job']:
                    continue
                if kind == 'result':
                    domain, ok, details = data
                    state['checked'] += 1
                    if ok and domain not in state['found']:
                        state['found'].add(domain)
                        global_results[:] = sorted(state['found'])
                        lbl_domains_val.configure(text=str(len(state['found'])))
                        write(text_output, f"[{state['checked']}] [+] {domain}")
                        btn_save.configure(state="normal")
                        if not state['paused']:
                            jumlah = len(state['found'])
                            status_progress[0] = f'[RUNNING] [GET] {jumlah} Domain'
                            render_status()
                elif kind == 'info':
                    write(status_output, data)
                elif kind == 'error':
                    write(status_output, '[ERROR] ' + data)
                elif kind == 'ping':
                    state['last_ping'] = data
                    lbl_ms_val.configure(text=data)
                elif kind == 'done':
                    finish(data)
        except queue.Empty:
            pass
        if state['running']:
            stop_at = state['pause_since'] if state['pause_since'] is not None else time.monotonic()
            elapsed = max(0, int(stop_at - state['started'] - state['paused_total']))
            mins, secs = divmod(elapsed, 60)
            lbl_time_val.configure(text=f"{mins:02d}:{secs:02d}")
        try:
            root.after(100, process_events)
        except (tk.TclError, RuntimeError):
            pass

    def ping_worker():
        while not session_cancel.is_set():
            ms = 'N/A (Offline)'
            for host, port in [('1.1.1.1', 443), ('8.8.8.8', 53), ('1.1.1.1', 53)]:
                try:
                    start = time.perf_counter()
                    with socket.create_connection((host, port), timeout=2.0):
                        pass
                    ms = f'{(time.perf_counter()-start)*1000:.0f} ms'
                    break
                except OSError:
                    continue
            events.put(('ping', state['job'], ms))
            session_cancel.wait(3)

    # Generator nama domain 4-50 karakter: bertahap (lazy), deduplikasi,
    # dan tidak membangun jutaan kombinasi dalam RAM sekaligus.
    def iter_prefixes():
        from itertools import product

        # Global-first multilingual bank (ASCII/romanized to fit DNS labels).
        words = """
        global world international universal united central main prime premier
        premium elite modern future new next first one group team hub network link
        connect bridge nexus synergy partner alliance union collective community society
        people public open united trusted trust secure safe reliable quality professional
        enterprise business company corporate ventures venture venturelab commerce trade trading
        retail wholesale supply supplier source solutions service services support help assist customer
        client market marketplace shop store shopping sales deals discount offers promo value savings budget
        price pricing payment pay wallet cash money finance financial banking capital credit invest investor
        investment wealth fund funds assets asset stock exchange accounting tax invoice billing insurance legal
        law justice policy contract logistics transport shipping delivery courier express fast rapid
        quick speed instant freight transit travel tourism trip journey voyage holiday hotel resort booking
        stay lodging rental rentals property properties realty realestate homes house housing apartment
        residence estate land farm agriculture farming harvest garden green clean eco nature natural energy power
        solar wind electric renewable climate earth planet environment recycle waste water ocean sea river
        lake mountain forest desert island city urban town village local regional metro district zone area place
        point spot square center central location map maps guide directory address finder discover explore search lookup
        index list catalog archive registry register records database data datas cloud hosting host server domain web
        website
        sites internet online mobile wireless wifi digital virtual remote cyber computer hardware software device platform
        application apps system systems process engine core infrastructure technology tech innovation innovative innovate
        ideas creative creativity design designs studio media social viral content contenthub news press magazine journal
        blog post story stories video photo image imaging audio music sound radio podcast stream streaming live
        broadcast channel tv show event events festival culture art arts gallery museum fashion lifestyle
        style beauty cosmetics spa wellness health healthcare care clinic medical medicine
        pharmacy doctor dental fitness fit gym workout yoga sport sports soccer football
        basketball tennis golf cycling running swimming esports gaming gamer games play
        entertainment fun club arena stadium education learning learn school academy
        college university campus class courses course lesson tutorial training
        skill skills jobs career hiring recruitment work office productivity project
        projects task tasks teamwork management manager admin automation automations analytic analytics analysis
        metrics report reporting stats statistic monitor monitoring tracker tracking dashboard portal console
        toolbox toolkit tools builder maker creator generator helper assistant smart intelligent ai aiagent robotics
        robot bot science research lab laboratory developer development dev code coder coding script scripts programming
        program appdev opensource sourcecloud api backend frontend fullstack framework security privacy protect protection
        shield defense safety auth identity account login verify verification check checker audit audits compliance
        certificate
        ssl tls dns domainname nameserver cloudnative saas paas iaas ecommerce fintech edtech medtech proptech foodtech
        agritech
        insuretech legaltech healthtech marketplacehub discovery digitalworld techworld webworld globallink
        sun sunrise sunset moon lunar solar star stellar galaxy cosmic cosmos space orbit nova comet planet earth sky skies
        blue red green
        gold golden silver amber azure aqua ocean coast beach wave waves tide marine coral fish shell pearl rock stone
        crystal diamond jewel gem snow ice frost winter summer spring autumn rain rainy storm thunder lightning cloud clouds
        mist fog air breeze wind winds fire flame ember blaze light bright shadow night day dawn dusk leaf leaves tree trees
        wood forest jungle bloom blossom flower flowers rose lily lotus orchid tulip ivy moss fern grass meadow field valley
        hill hills peak summit mountain river rivers stream creek waterfall lake lakes pond island islands tropic tropical
        palm cedar pine maple oak willow birch bamboo safari wild wildlife animal animals bird birds eagle falcon hawk owl
        raven crow lion tiger wolf fox panda bear deer horse dolphin shark whale butterfly bee honey pet pets cat dog puppy
        kitten farm garden grove orchard fruit fruits apple orange lemon lime berry cherry grape melon peach mango coconut
        kiwi pineapple mint basil sage tea coffee bean beans sugar spice salt pepper ginger cinnamon vanilla chocolate cocoa
        caramel cream milk bread bakery bake baker kitchen dining dinner breakfast lunch cafe restaurant bistro food foods
        fresh organic pure purity simple balance harmony serenity zen bliss joy happy smile lucky fortune dream dreams hope
        faith love heart soul spirit mind mindful focus wisdom brave courage bold strength strong mighty giant grand royal
        crown king queen hero legend epic myth magic mystic wonder marvel brilliant sparkle spark glow shine vivid vibrant
        dynamic kinetic sonic pulse rhythm beat flow drift roam wander rise rising grow growth thrive prosper progress
        evolve evolution genesis origin start launch begin emerge inspire inspiration imagine vision clarity clear true
        truth honest kind kindness good better best excellence flawless perfect luxury luxe classic timeless vintage retro
        neon pixel turbo ultra mega micro nano hyper super max mini basic essential select exclusive limited rare unique
        distinct original authentic genuine genuinegold
        bonjour merci amour soleil maison monde etoile lumiere fleur coeur rouge bleu blanc noir vert argent orage bonheur
        avenir nouveau petite grand esprit belle jolie vie voyage nuit jour etoile cielo sol luna estrella mundo vida amor
        amigo amiga amigos alegria feliz bueno buena nuevo nueva grande casa hogar calle camino playa playaazul mar ola rio
        montana bosque tierra fuego agua aire luz oro plata felizvida rapido verde blanco negro azul rosa bello bella
        familia trabajo dinero banco mercado tienda tiendaonline mundoonline rapido futuro maisonbleue guten tag hallo
        willkommen welt liebe freund freunde stern himmel licht sonne mond wasser feuer berg wald haus stadt land zeit neue
        neu gut kraft schnell wunderbar schoen frei glück joyeux mondeglobal casa bella dolce vita ciao grazie buongiorno
        bella bene sole luna mare fiore cuore verde rosso bianco nero azzurro oro argento nuovo grande piccolo veloce forte
        vita mondo futuro bravo grazie citta amico lavoro viaggio luce notte giorno buongiorno buenos dias hola mundo amigo
        alegre rapido bello bonita bueno buena nueva nuevo playa montana cielo estrella corazon corazonverde vida libre
        fuerza fuerte futuro mercado tienda casa camino caminoverde azul oro plata rojo negro blanco rapido saludable
        bonjourmonde aloha mahalo ohana mana kai moana hana nui pono malama loka loko aina pilina kawaii yume hikari sora
        umi hana kokoro mirai sekai hoshi tsuki taiyo kaze mizu yama mori sakura hana hanae kumo shiro kuro aka ao midori
        neko inu kitsune tanuki yuki haru natsu aki fuyu hikari takara kibo asahi sora noor nur hayat dunya salam aman safar
        sahara bazaar zaitun bahr qamar shams najma nurani sahil rahma baraka habibi khaleej alif nizam ilm kitab qalam
        zaman asman gul bahar shanti namaste ananda naya navi sundar sundari jyoti utsav mitra bazar duniya rang roshni
        tejas tara nadi van vanya jal agni akash shakti prana sukh khushi sansar
        america american canada canadian mexico mexican brazil brasil argentina chile peru colombia europe european asia
        asian africa african oceania australia australian newzealand zealand indonesia indonesian singapore singaporean
        malaysia malaysian thailand thai vietnam vietnamese cambodia cambodian philippines philippine japan japanese korea
        korean china chinese india indian pakistan pakistanian bangladesh nepal sri lanka srilanka taiwan taiwanese hongkong
        hongkonger turkey turkish emirates dubai abu dhabi arab arabia saudi qatar oman kuwait egypt egyptian morocco maroc
        nigeria kenya southafrica europeglobal germany german france french italy italian spain spanish portugal portuguese
        netherlands dutch belgium belgian switzerland swiss austria austrian sweden swedish norway norwegian denmark danish
        finland finnish iceland icelandic ireland irish britain british england english scotland scottish wales welsh
        unitedkingdom london paris berlin rome madrid lisbon amsterdam brussels vienna zurich geneva stockholm oslo
        copenhagen helsinki reykjavik dublin edinburgh manchester birmingham liverpool barcelona milan venice florence
        naples athens prague budapest warsaw krakow bucharest istanbul ankara cairo casablanca nairobi lagos accra capetown
        johannesburg sydney melbourne brisbane perth auckland wellington toronto vancouver montreal ottawa quebec newyork
        york losangeles california sanfrancisco seattle chicago boston miami houston dallas austin atlanta washington
        florida texas vegas lasvegas denver phoenix detroit tokyo osaka kyoto yokohama nagoya sapporo seoul busan beijing
        shanghai shenzhen guangzhou hongkong taipei bangkok phuket hanoi saigon hochiminh danang singaporecity kualalumpur
        jakarta bali surabaya bandung medan yogyakarta makassar medan manila cebu dhaka karachi mumbai delhi newdelhi
        bengaluru bangalore chennai hyderabad kolkata kathmandu colombo riyadh jeddah doha abu dhabi muscat
        aero aerojet astral astro atom atomic axiom axis apex vertex vector vivid volta volt vera verity vox voxel vista
        vision zenith zephyr zetta zeno zoom zuma zora zuri ziva zio zent zenro zento vanta vanto velora velox velo vera
        vero veris verix verio viora vario varis vistra vitra vitalis vida vidaa novex novara novio novus nexio nexa nexora
        nexon nexify nexora norix norton omni omnic omnihub orbix orbis orbit orion ozora ozen opal optimum optimus optima
        optimix prisma prism pixora pixio pixen pixelia pluto pulse pulso quanta quantum qubit quora qira qura qualia quadra
        qnix radix radar radon rayna rayzo raina renova renox rexora rivora rovia rovo riko roza roko sakura sequoia serra
        sero serix sigma sima sora sorix sova solix solara solora solvex synta synex synora synera synthio tera terrix terro
        terra terrax tesla titan torix tria trixo truva truvo ultra ultrix uma uno urban urba urbix urion utara varia valora
        vega vegax veda veltra venora venox viara vividra xenon xeno xenora xentrix xiva xora xovia yotta yura yuma yuno
        yovia yuzra zaira zentra zentry zentrix zilra zinox zivra zoria zovo zynex zynora zyntra
        pusat toko rumah sukses berkah global prima mitra sumber karya utama
        mandiri abadi sejahtera digital solusi cipta kreatif media portal nusantara
        bisnis sistem anugerah bintang sentral online shop store market group
        indonesia terpercaya terbaik express kilat jaya makmur teknologi official
        super mega finansial investasi properti kesehatan wisata kuliner fashion
        teknik logistik artha dana cash wallet bank kredit modal aura cahaya
        sakti indah lestari buana alam sari raya perdana niaga link connect
        hub station cloud data smart fast quick easy auto bot cyber secure
        safe shield trust alpha prime top best next hoki win play game
        sport bola live stream blog news info code dev lab studio factory
        works craft build design art style food cafe resto fresh green bio
        eco health care fit gym spa beauty travel tour pesona bahagia
        sentosa gemilang inspirasi karsa andalan berdikari pioner inovasi
        visioner strategi inovatif modern unggul maju hemat praktis nasional
        internasional lokal daerah komunitas indonesia layanan service solusi
        jaringan hosting domain server website aplikasi program perangkat
        komputer mesin tokoonline tokodigital belanja murah diskon promo
        spesial eksklusif pilihan favorit unggulan terbaru populer resmi
        original kualitas cepat aman mudah terpercaya tangguh optimal
        bisnisdigital ecommerce pembayaran transaksi finansial keuangan
        tabungan investasi teknologi informasi pendidikan sekolah kampus
        universitas pelatihan belajar kursus materi pengetahuan ilmu
        kesehatan klinik dokter apotek farmasi herbal olahraga kebugaran
        perjalanan transportasi pengiriman ekspedisi kendaraan otomotif
        motor mobil sepeda rental penginapan hotel resort restoran
        makanan minuman kopi teh kue roti nasi ayam ikan sayuran
        pertanian perkebunan perikanan peternakan industri pabrik produksi
        konstruksi bangunan arsitektur interior dekorasi furniture mebel
        properti tanah rumahku apartemen hunian perumahan keluarga
        sahabat teman bersama bersatu kemitraan kerjasama kolaborasi
        komunitas kreasi inovator pengembang developer agency konsultan
        pemasaran marketing penjualan promosi iklan konten kreator
        fotografi videografi sinema musik audio visual hiburan acara
        event festival pertunjukan berita majalah koran jurnal artikel
        pustaka perpustakaan buku baca tulis cerita inspirasi motivasi
        platform marketplace direktori katalog referensi database
        automasi integrasi sinkronisasi analitik statistik laporan
        monitoring pengawasan manajemen administrasi organisasi
        perusahaan korporasi enterprise startup bisnisusaha usaha
        
        """.split()
        # Priority: universal global vocabulary, then international terms, then regional words.
        words = list(dict.fromkeys(w.lower() for w in words if w.isascii() and w.isalpha()))
        suffixes = ('id', 'go', 'pro', 'net', 'web', 'app', 'online', 'shop', 'store',
                    'digital', 'official', 'indo', '2026', '2027', '88', '99', '123', '168')
        prefixes = ('my', 'the', 'go', 'get', 'indo', 'neo', 'max', 'best', 'top',
                    'smart', 'super', 'mega', 'auto', 'e', 'i')
        seen = set()

        def valid(candidate):
            return (4 <= len(candidate) <= 50 and
                    candidate[0].isalnum() and candidate[-1].isalnum() and
                    all(c.isascii() and (c.islower() or c.isdigit() or c == '-') for c in candidate))

        def unique(items):
            for item in items:
                if valid(item) and item not in seen:
                    seen.add(item)
                    yield item

        yield from unique(words)
        yield from unique(w + ending for w in words for ending in suffixes)
        yield from unique(begin + w for w in words for begin in prefixes)
        yield from unique(a + b for a in words for b in words if a != b)
        # Dua sampai empat kata untuk mencakup nama panjang (hingga 50 huruf).
        # Kombinasi panjang dibatasi pada kosakata pilihan supaya tetap terkendali.
        common = words[:90]
        yield from unique(a + b + c for a in common for b in common[:45]
                          for c in common[:12] if len(a) + len(b) + len(c) <= 50)
        yield from unique(a + b + c + d for a in common[:35]
                          for b in common[:25] for c in common[:12]
                          for d in common[:6]
                          if len(a) + len(b) + len(c) + len(d) <= 50)
        # Panjang persis 50 didukung oleh validasi yang sama.

        # Nama generik empat karakter, bermanfaat untuk nama singkat.
        for chars in product('abcdefghijklmnopqrstuvwxyz', repeat=4):
            candidate = ''.join(chars)
            if candidate not in seen:
                seen.add(candidate)
                yield candidate


    def scan_worker(job, scan_mode, tld, tld_mode):
        # Generator menghasilkan kandidat secara bertahap; tidak menaruh semua
        # kombinasi kata x TLD dalam RAM sekaligus.
        try:
            if tld_mode == 'Semua TLD':
                selected_tlds = ALL_FINDER_TLDS
            elif tld_mode == 'Random':
                selected_tlds = ALL_FINDER_TLDS
            else:
                selected_tlds = (tld,)

            if scan_mode == 'CRT.SH':
                selected = (random.choice(selected_tlds),) if tld_mode == 'Random' else selected_tlds
                for idx, suffix in enumerate(selected, 1):
                    if session_cancel.is_set() or job != state['job']:
                        break
                    while state['paused'] and not session_cancel.is_set():
                        time.sleep(.15)
                    try:
                        response = requests.get('https://crt.sh/',
                            params={'q': '%.' + suffix, 'output': 'json'}, timeout=45)
                        response.raise_for_status()
                        for entry in response.json():
                            if session_cancel.is_set() or job != state['job']:
                                break
                            while state['paused'] and not session_cancel.is_set():
                                time.sleep(.15)
                            for sub in str(entry.get('name_value', '')).splitlines():
                                if '*' in sub:
                                    continue
                                domain = extract_root_domain(sub, suffix)
                                if domain:
                                    events.put(('result', job, (domain, True, 'CRT.SH')))
                    except (requests.RequestException, ValueError) as exc:
                        events.put(('info', job, f'[SKIP] .{suffix}: {exc}'))
            else:
                def check_one(domain):
                    try:
                        socket.getaddrinfo(domain, 80, type=socket.SOCK_STREAM)
                        return (domain, True, 'DNS resolved')
                    except OSError:
                        return (domain, False, '')

                def domain_candidates():
                    for prefix in iter_prefixes():
                        if tld_mode == 'Random':
                            yield prefix + '.' + random.choice(selected_tlds)
                        else:
                            for suffix in selected_tlds:
                                yield prefix + '.' + suffix

                candidates = domain_candidates()
                with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                    pending = set()
                    exhausted = False
                    submitted = 0
                    while (not exhausted or pending) and not session_cancel.is_set() and job == state['job']:
                        while state['paused'] and not session_cancel.is_set():
                            time.sleep(.15)
                        if session_cancel.is_set():
                            break
                        while len(pending) < 40 and not exhausted and not state['paused']:
                            try:
                                domain = next(candidates)
                            except StopIteration:
                                exhausted = True
                                break
                            pending.add(executor.submit(check_one, domain))
                            submitted += 1
                        if pending:
                            finished, pending = concurrent.futures.wait(pending, timeout=.25,
                                return_when=concurrent.futures.FIRST_COMPLETED)
                            for future in finished:
                                if session_cancel.is_set():
                                    break
                                events.put(('result', job, future.result()))
            if not session_cancel.is_set() and job == state['job']:
                events.put(('done', job, '[DONE] Scan selesai. Hasil siap disimpan.'))
        except Exception as exc:
            events.put(('error', job, str(exc)))
            events.put(('done', job, '[DONE] Scan berhenti karena error.'))

    def scan():
        if state['running']:
            return
        mode = mode_var.get()
        tld_mode = tld_mode_var.get()
        suffix = entry_tld.get().strip().lower().lstrip('.')
        if mode == 'NONE' or tld_mode == 'NONE':
            messagebox.showwarning('Pengaturan belum lengkap', 'Pilih mode scan dan mode TLD terlebih dahulu.', parent=root)
            return
        if tld_mode == 'Manual' and not suffix:
            messagebox.showwarning('TLD kosong', 'Masukkan TLD, misalnya com atau co.id.', parent=root)
            return
        if tld_mode in ('Random', 'Semua TLD'):
            suffix = ''
        status_progress[0] = '[RUNNING] [GET] 0 Domain'
        state.update(running=True, paused=False, started=time.monotonic(), found=set(), checked=0,
                     pause_since=None, paused_total=0.0)
        state['job'] += 1
        session_cancel.clear()
        global_results.clear()
        text_output.configure(state='normal')
        text_output.delete('0.0', 'end')
        text_output.configure(state='disabled')
        lbl_domains_val.configure(text='0')
        lbl_time_val.configure(text='00:00')
        btn_save.configure(state='disabled')
        btn_search.configure(state='disabled', text='Scanning...')
        btn_pause_resume.configure(state='normal', text='Pause')
        write(status_output, f'[START] Starting {mode} scan...')
        if tld_mode == 'Semua TLD':
            write(status_output, f'[TLD] Semua TLD aktif: {len(ALL_FINDER_TLDS)} ekstensi.')
        render_status()
        threading.Thread(target=scan_worker, args=(state['job'], mode, suffix, tld_mode), daemon=True).start()

    def pause():
        if not state['running']:
            return
        state['paused'] = not state['paused']
        if state['paused']:
            state['pause_since'] = time.monotonic()
            status_progress[0] = None
            write(status_output, '[PAUSED] Pemindaian dijeda oleh user.')
        else:
            if state['pause_since'] is not None:
                state['paused_total'] += time.monotonic() - state['pause_since']
            state['pause_since'] = None
            write(status_output, '[RESUMED] Pemindaian dilanjutkan.')
            status_progress[0] = f'[RUNNING] [GET] {len(state["found"])} Domain'
            render_status()
        btn_pause_resume.configure(text='Resume' if state['paused'] else 'Pause')

    def clear():
        status_history.clear()
        status_progress[0] = None
        state['job'] += 1
        session_cancel.set()
        state.update(running=False, paused=False, started=0, found=set(), checked=0,
                     pause_since=None, paused_total=0.0)
        global_results.clear()
        for widget in (text_output, status_output):
            widget.configure(state='normal')
            widget.delete('0.0', 'end')
            widget.configure(state='disabled')
        lbl_domains_val.configure(text='0')
        lbl_time_val.configure(text='00:00')
        btn_save.configure(state='disabled')
        btn_search.configure(state='normal', text='🔍 Scan')
        btn_pause_resume.configure(state='disabled', text='Pause')
        write(status_output, '[SYSTEM] Finder Ready')
        write(status_output, '[STATUS] Waiting for configuration')
        # Keep ping monitor active; scanning cancellation is tied to job id.
        session_cancel.clear()

    def save():
        if not state['found']:
            messagebox.showwarning('Peringatan', 'Belum ada hasil domain untuk disimpan.', parent=root)
            return
        path = filedialog.asksaveasfilename(parent=root, defaultextension='.txt',
                 filetypes=[('Text Files', '*.txt')], title='Simpan hasil Finder')
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as file:
                    file.write('\n'.join(sorted(state['found'])) + '\n')
                write(status_output, f'[SAVE SUCCESS] {len(state["found"])} domain berhasil disimpan.')
                write(status_output, f'[FILE] {__import__("os").path.basename(path)}')
            except OSError as exc:
                messagebox.showerror('Gagal menyimpan', str(exc), parent=root)

    def close():
        if state['closed']:
            return
        state['closed'] = True
        state['job'] += 1
        session_cancel.set()
        if on_back:
            on_back()
        else:
            root.destroy()

    btn_search.configure(command=scan)
    btn_pause_resume.configure(command=pause)
    btn_clear.configure(command=clear)
    btn_save.configure(command=save)
    for button in (btn_search, btn_pause_resume, btn_save, btn_clear):
        button.pack(side='left', padx=(0, 6))
    ctk.CTkButton(actions, text='🚪 Logout', command=close, width=100, height=29,
                  fg_color='#c92a2a', hover_color='#a61e1e', font=FONT).pack(side='right')
    root.protocol('WM_DELETE_WINDOW', close)
    root.after(100, process_events)
    threading.Thread(target=ping_worker, daemon=True).start()
    return root

if __name__ == "__main__":
    # Modul Finder hanya digunakan melalui launcher aplikasi.py.
    print("ACCESS DENIED: Buka Finder melalui aplikasi.py.")
    raise SystemExit(1)