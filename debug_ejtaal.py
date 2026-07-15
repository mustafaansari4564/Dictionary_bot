"""
debug_ejtaal.py — Run this on your KeritCloud server to diagnose image loading.

Usage:
    python debug_ejtaal.py

Paste the full output here so we can pick the right fix.
"""

import urllib.request
import urllib.error
import socket

TEST_IMAGE = "https://ejtaal.net/aa/img/umj/umj0034.jpg"   # first Al-Munjid page

TESTS = [
    ("No headers",
     {}),
    ("Browser User-Agent",
     {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}),
    ("With Referer",
     {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "Referer":    "https://ejtaal.net/aa/"}),
    ("Full browser headers",
     {"User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "Referer":         "https://ejtaal.net/aa/",
      "Accept":          "image/webp,image/apng,image/*,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9",
      "Accept-Encoding": "gzip, deflate, br"}),
]

PROXIES = [
    ("wsrv.nl (no referer)",
     f"https://wsrv.nl/?url=ejtaal.net/aa/img/umj/umj0034.jpg"),
    ("wsrv.nl + referer param",
     f"https://wsrv.nl/?url=ejtaal.net/aa/img/umj/umj0034.jpg&referer=https://ejtaal.net/aa/"),
    ("images.weserv.nl",
     f"https://images.weserv.nl/?url=ejtaal.net/aa/img/umj/umj0034.jpg"),
    ("imageproxy.app",
     f"https://imageproxy.app/img?url=https://ejtaal.net/aa/img/umj/umj0034.jpg"),
]

def try_url(label, url, headers=None):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=12) as r:
            data  = r.read(512)
            ctype = r.headers.get("content-type", "?")
            size  = r.headers.get("content-length", "?")
            print(f"  ✅  {label}")
            print(f"       status={r.status}  content-type={ctype}  length={size}")
            is_jpg = data[:3] == b'\xff\xd8\xff'
            is_png = data[:4] == b'\x89PNG'
            print(f"       real image: {'yes (JPEG)' if is_jpg else 'yes (PNG)' if is_png else 'NO — got HTML/text?'}")
            return True
    except urllib.error.HTTPError as e:
        print(f"  ❌  {label}  →  HTTP {e.code} {e.reason}")
    except urllib.error.URLError as e:
        print(f"  ❌  {label}  →  URLError: {e.reason}")
    except socket.timeout:
        print(f"  ❌  {label}  →  Timeout")
    except Exception as e:
        print(f"  ❌  {label}  →  {type(e).__name__}: {e}")
    return False

print("=" * 60)
print("  ejtaal.net image debug")
print(f"  Test URL: {TEST_IMAGE}")
print("=" * 60)

print("\n── Direct ejtaal.net (different headers) ──────────────────")
for label, headers in TESTS:
    try_url(label, TEST_IMAGE, headers)

print("\n── Image proxies ───────────────────────────────────────────")
for label, url in PROXIES:
    try_url(label, url, {"User-Agent": "Mozilla/5.0"})

print("\n── Network info ────────────────────────────────────────────")
try:
    ip = socket.gethostbyname("ejtaal.net")
    print(f"  ejtaal.net resolves to: {ip}")
except Exception as e:
    print(f"  DNS lookup failed: {e}")

try:
    my_ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode()
    print(f"  This server's public IP: {my_ip}")
except Exception as e:
    print(f"  Could not get public IP: {e}")

print("\n" + "=" * 60)
print("  Paste full output above to diagnose the issue.")
print("=" * 60)