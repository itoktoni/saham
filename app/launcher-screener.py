#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
launcher-screener.py
====================
Launcher tipis untuk "Screener Saham.exe".

Saat diklik, menjalankan app/app-screener.py memakai Python yang terinstal
(pythonw bila ada, agar tanpa jendela hitam), BUKAN kode hasil compile.
Akibatnya: edit web/*.html atau scripts/*.py langsung berlaku tanpa
rebuild exe. Satu-satunya syarat: Python 3.8+ ada di PATH.

Dibangun dengan:
  python -m PyInstaller --noconfirm --onefile --windowed ^
    --name "Screener Saham" app\\launcher-screener.py
"""

import os
import shutil
import subprocess
import sys

DETACHED_PROCESS = 0x00000008


def salah(pesan):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, pesan, "Screener Saham", 0x10)
    except Exception:
        pass
    sys.exit(1)


def server_jalan():
    """Kembalikan URL server Screener yang sudah hidup (atau None).

    Mencegah server menumpuk: tiap server menempati port baru (8765, 8766, ...)
    dan tiap port punya riwayat umur/fase sendiri di browser.
    """
    import json
    import urllib.request
    for port in range(8765, 8777):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/api/status" % port,
                                        timeout=0.5) as r:
                if json.loads(r.read().decode("utf-8", "replace")).get("app"):
                    return "http://127.0.0.1:%d/" % port
        except Exception:  # noqa: BLE001
            continue
    return None


def main():
    hidup = server_jalan()
    if hidup:
        import webbrowser
        webbrowser.open(hidup)
        return 0
    if getattr(sys, "frozen", False):
        root = os.path.dirname(os.path.abspath(sys.executable))
    else:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target = os.path.join(root, "app", "app-screener.py")
    if not os.path.isfile(target):
        salah("Tidak ditemukan:\n%s\n\nJalankan exe dari folder Screener." % target)
    exe = shutil.which("pythonw") or shutil.which("python")
    if not exe:
        salah("Python tidak ditemukan di PATH.\n\nPasang Python 3.8+ "
              "(centang 'Add to PATH') lalu klik exe ini lagi.")
    try:
        subprocess.Popen([exe, target], cwd=root,
                         creationflags=DETACHED_PROCESS, close_fds=True)
    except Exception as e:  # noqa: BLE001
        salah("Gagal menjalankan Screener:\n%s" % e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
