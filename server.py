"""Read-only LAN server for lab docs. Run: python server.py  (port 8000)"""
import html, os, socket, sys, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import markdown

ROOTS = {
    "tai-lieu": (r"D:\Downloads\tài liệu", "Tài liệu"),
    "devops": (r"D:\Downloads\Devops", "Devops"),
}
EXCLUDE = [os.path.normcase(os.path.abspath(r"D:\Downloads\Devops\Lab"))]
ALLOWED = {".md", ".html", ".htm", ".txt", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

CSS = """
:root{--bg:#fff;--fg:#1f2328;--muted:#656d76;--card:#f6f8fa;--border:#d0d7de;--link:#0969da}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--muted:#8d96a0;--card:#161b22;--border:#30363d;--link:#4493f8}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:900px;margin:0 auto;padding:16px}a{color:var(--link);text-decoration:none}
nav.crumb{font-size:14px;color:var(--muted);margin-bottom:12px;word-break:break-all}
ul.list{list-style:none;padding:0}ul.list li a{display:block;padding:12px 14px;margin:6px 0;background:var(--card);border:1px solid var(--border);border-radius:8px}
pre{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:12px;overflow-x:auto;font-size:13px}
code{font-family:ui-monospace,Consolas,monospace;font-size:0.9em}:not(pre)>code{background:var(--card);padding:1px 5px;border-radius:4px}
table{border-collapse:collapse;display:block;overflow-x:auto;max-width:100%}th,td{border:1px solid var(--border);padding:6px 10px}
img{max-width:100%}blockquote{margin:0;padding-left:12px;border-left:4px solid var(--border);color:var(--muted)}
h1,h2,h3{line-height:1.3}h1{font-size:1.6em}h2{font-size:1.35em;border-bottom:1px solid var(--border);padding-bottom:4px}
.top{position:fixed;right:14px;bottom:14px;background:var(--card);border:1px solid var(--border);border-radius:50%;width:44px;height:44px;display:flex;align-items:center;justify-content:center}
"""


def page(title, crumb, body):
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body><main><nav class="crumb">{crumb}</nav>{body}</main>
<a class="top" href="#">↑</a></body></html>""".encode("utf-8")


def excluded(path):
    p = os.path.normcase(os.path.abspath(path))
    return any(p == e or p.startswith(e + os.sep) for e in EXCLUDE)


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parts = [p for p in urllib.parse.unquote(urllib.parse.urlparse(self.path).path).split("/") if p]
        if not parts:
            items = "".join(f'<li><a href="/{k}/">📁 {html.escape(v[1])}</a></li>' for k, v in ROOTS.items())
            return self.send(200, page("Lab docs", "🏠 Trang chủ", f"<h1>Tài liệu Lab</h1><ul class='list'>{items}</ul>"))
        if parts[0] not in ROOTS or any(p in ("..", ".") for p in parts):
            return self.send(404, page("404", "", "<h1>Không tìm thấy</h1>"))
        root = os.path.abspath(ROOTS[parts[0]][0])
        target = os.path.abspath(os.path.join(root, *parts[1:]))
        if not (target == root or target.startswith(root + os.sep)) or excluded(target) or not os.path.exists(target):
            return self.send(404, page("404", "", "<h1>Không tìm thấy</h1>"))

        crumb = '<a href="/">🏠</a>'
        acc = ""
        for i, p in enumerate(parts):
            acc += "/" + urllib.parse.quote(p)
            label = ROOTS[p][1] if i == 0 else p
            crumb += f' / <a href="{acc}/">{html.escape(label)}</a>' if i < len(parts) - 1 or os.path.isdir(target) else f" / {html.escape(p)}"

        if os.path.isdir(target):
            if not self.path.endswith("/"):
                self.send_response(301); self.send_header("Location", self.path + "/"); self.end_headers(); return
            dirs, files = [], []
            for name in sorted(os.listdir(target), key=str.lower):
                full = os.path.join(target, name)
                if name.startswith(".") or excluded(full):
                    continue
                if os.path.isdir(full):
                    dirs.append(f'<li><a href="{urllib.parse.quote(name)}/">📁 {html.escape(name)}</a></li>')
                elif os.path.splitext(name)[1].lower() in ALLOWED:
                    files.append(f'<li><a href="{urllib.parse.quote(name)}">📄 {html.escape(name)}</a></li>')
            body = f"<h1>{html.escape(parts[-1] if len(parts) > 1 else ROOTS[parts[0]][1])}</h1><ul class='list'>{''.join(dirs + files)}</ul>"
            return self.send(200, page(parts[-1], crumb, body))

        ext = os.path.splitext(target)[1].lower()
        if ext not in ALLOWED:
            return self.send(404, page("404", "", "<h1>Không tìm thấy</h1>"))
        with open(target, "rb") as f:
            data = f.read()
        if ext == ".md":
            text = data.decode("utf-8", errors="replace")
            body = markdown.markdown(text, extensions=["fenced_code", "tables", "toc", "sane_lists", "nl2br"])
            return self.send(200, page(parts[-1], crumb, body))
        types = {".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8", ".txt": "text/plain; charset=utf-8",
                 ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp"}
        return self.send(200, data, types[ext])

    def log_message(self, fmt, *args):
        sys.stdout.write(f"{self.client_address[0]} {fmt % args}\n")


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1)); return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    print(f"Mở trên điện thoại: http://{lan_ip()}:{PORT}/   (Ctrl+C để dừng)", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
