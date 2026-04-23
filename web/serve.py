#!/usr/bin/env python3.13
"""
Local dev server for web2/ that mimics Vercel's cleanUrls behavior.

Run from web2/ directory:
    python3.13 serve.py

Then open http://localhost:8000 on this Mac,
or http://<LAN-IP>:8000 from any device on the same Wi-Fi.

Ctrl+C to stop.
"""

import http.server
import socket
import socketserver
import os
from pathlib import Path

PORT = 8000
HOST = "0.0.0.0"  # listen on all interfaces so iPhone on same Wi-Fi can reach us

WEB_ROOT = Path(__file__).parent.resolve()


class CleanUrlsHandler(http.server.SimpleHTTPRequestHandler):
    """Mimics Vercel's cleanUrls=true: /foo -> /foo.html if foo.html exists."""

    def _maybe_rewrite(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        query = self.path[len(path):]
        if path != "/" and not path.endswith("/") and "." not in path.rsplit("/", 1)[-1]:
            candidate = (WEB_ROOT / path.lstrip("/")).with_suffix(".html")
            if candidate.is_file():
                self.path = path + ".html" + query

    def do_GET(self):
        self._maybe_rewrite()
        return super().do_GET()

    def do_HEAD(self):
        self._maybe_rewrite()
        return super().do_HEAD()

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def get_lan_ip() -> str | None:
    """Best-effort detection of this Mac's LAN IP (e.g. 192.168.x.x)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # no packet actually sent for UDP connect
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


def main():
    os.chdir(WEB_ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), CleanUrlsHandler) as httpd:
        lan_ip = get_lan_ip()
        print("=" * 60)
        print(f"BagHolderAI web2/ dev server")
        print(f"Serving {WEB_ROOT}")
        print("-" * 60)
        print(f"  Local:     http://localhost:{PORT}")
        if lan_ip:
            print(f"  Wi-Fi:     http://{lan_ip}:{PORT}   (iPhone/iPad same network)")
        print("-" * 60)
        print("cleanUrls rewrite active: /dashboard -> dashboard.html")
        print("Ctrl+C to stop.")
        print("=" * 60)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
