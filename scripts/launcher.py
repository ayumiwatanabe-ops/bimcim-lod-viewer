# -*- coding: utf-8 -*-
"""ビューア起動ランチャー
   自分と同じフォルダを 127.0.0.1 の簡易 Web サーバで公開し、既定のブラウザで index.html を開く
   (index.html は file:// では動かないため)。PyInstaller で exe 化して配布する。
"""
import os, sys, socket, threading, webbrowser, http.server, socketserver, time

BASE = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
INDEX = os.path.join(BASE, "index.html")

def free_port(start=8765):
    for p in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0: return p
    return 0

class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".glb": "model/gltf-binary", ".json": "application/json", ".js": "text/javascript"}
    def __init__(self, *a, **k): super().__init__(*a, directory=BASE, **k)
    def log_message(self, *a): pass
    def end_headers(self):
        self.send_header("Cache-Control", "no-store"); super().end_headers()

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True; daemon_threads = True

def main():
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk(); root.title("BIM/CIM 詳細度サンプルビューア"); root.geometry("460x210"); root.resizable(False, False)
    if not os.path.exists(INDEX):
        messagebox.showerror("起動できません", f"同じフォルダに index.html が見つかりません。\n\nこの exe は、GitHub からダウンロードした ZIP を展開したフォルダ\n(index.html と models フォルダがある場所) に置いて実行してください。\n\n場所: {BASE}")
        root.destroy(); return
    port = free_port()
    if not port:
        messagebox.showerror("起動できません", "空いているポートが見つかりませんでした。"); root.destroy(); return
    srv = Server(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/index.html"
    tk.Label(root, text="ビューアを起動しました", font=("Yu Gothic UI", 13, "bold")).pack(pady=(16, 4))
    tk.Label(root, text="ブラウザが自動で開きます。開かない場合は下のボタンを押してください。", font=("Yu Gothic UI", 9)).pack()
    e = tk.Entry(root, font=("Consolas", 10), width=40, justify="center"); e.insert(0, url); e.configure(state="readonly"); e.pack(pady=6)
    f = tk.Frame(root); f.pack(pady=6)
    tk.Button(f, text="ブラウザで開く", width=16, command=lambda: webbrowser.open(url)).grid(row=0, column=0, padx=6)
    tk.Button(f, text="終了", width=12, command=root.destroy).grid(row=0, column=1, padx=6)
    tk.Label(root, text="このウィンドウを閉じるとビューアは終了します（ブラウザは閉じて構いません）", font=("Yu Gothic UI", 8), fg="#666").pack(pady=(4, 0))
    root.after(400, lambda: webbrowser.open(url))
    root.mainloop()
    srv.shutdown()

if __name__ == "__main__":
    main()
