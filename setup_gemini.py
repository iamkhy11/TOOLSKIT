"""Configure Gemini access for J Ai without embedding credentials in source code."""
import getpass
import os
import sys


def main():
    if os.name != 'nt':
        print('Script ini untuk Windows. Pada OS lain, atur GEMINI_API_KEY sebagai environment variable.')
        return 1
    key = getpass.getpass('Tempel Gemini API Key BARU (input disembunyikan): ').strip()
    if not key:
        print('Dibatalkan: tidak ada key.')
        return 1
    import winreg
    path = r'Environment'
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as reg:
        winreg.SetValueEx(reg, 'GEMINI_API_KEY', 0, winreg.REG_SZ, key)
    # Notify newly opened processes about user environment change.
    try:
        import ctypes
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        result = ctypes.c_ulong()
        ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0,
            'Environment', SMTO_ABORTIFHUNG, 2000, ctypes.byref(result))
    except Exception:
        pass
    print('Gemini API Key terpasang untuk akun Windows ini. Tutup dan jalankan ulang aplikasi.py.')
    print('Jangan membagikan environment variable atau API Key kepada pengguna lain.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
