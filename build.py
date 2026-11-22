"""Build static site from lab docs into ./docs (for GitHub Pages).
Run: python build.py
"""
import html, os, re, shutil, urllib.parse
import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs")
ROOTS = [
    ("tai-lieu", r"D:\Downloads\tài liệu", "Tài liệu"),
    ("devops", r"D:\Downloads\Devops", "Devops"),
]
EXCLUDE = [os.path.normcase(os.path.abspath(r"D:\Downloads\Devops\Lab"))]
COPY_EXT = {".html", ".htm", ".txt", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

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
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body><main><nav class="crumb">{crumb}</nav>{body}</main>
<a class="top" href="#">↑</a></body></html>"""


def excluded(path):
    p = os.path.normcase(os.path.abspath(path))
    return any(p == e or p.startswith(e + os.sep) for e in EXCLUDE)


def crumb(parts, label0, is_file):
    """parts: path segments under site root (excluding file name if is_file)."""
    depth = len(parts)
    up = lambda n: "../" * n or "./"
    out = f'<a href="{up(depth)}index.html">🏠</a>'
    for i, p in enumerate(parts):
        label = label0 if i == 0 else p
        if i == depth - 1 and not is_file:
            out += f" / {html.escape(label)}"
        else:
            out += f' / <a href="{up(depth - i - 1)}index.html">{html.escape(label)}</a>'
    return out


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def build_dir(src, rel_parts, label0):
    dst = os.path.join(OUT, *rel_parts)
    os.makedirs(dst, exist_ok=True)
    dirs, files = [], []
    for name in sorted(os.listdir(src), key=str.lower):
        full = os.path.join(src, name)
        if name.startswith(".") or excluded(full):
            continue
        if os.path.isdir(full):
            if build_dir(full, rel_parts + [name], label0):
                dirs.append(f'<li><a href="{urllib.parse.quote(name)}/index.html">📁 {html.escape(name)}</a></li>')
            continue
        base, ext = os.path.splitext(name)
        ext = ext.lower()
        if ext == ".md":
            with open(full, encoding="utf-8", errors="replace") as f:
                body = markdown.markdown(f.read(), extensions=["fenced_code", "tables", "toc", "sane_lists", "nl2br"])
            # local links to other .md files -> generated .md.html
            body = re.sub(r'href="(?!https?:)([^"#]+\.md)(#[^"]*)?"', lambda m: f'href="{m.group(1)}.html{m.group(2) or ""}"', body)
            out_name = name + ".html"
            write(os.path.join(dst, out_name), page(name, crumb(rel_parts, label0, True) + f" / {html.escape(name)}", body))
            files.append(f'<li><a href="{urllib.parse.quote(out_name)}">📄 {html.escape(name)}</a></li>')
        elif ext in COPY_EXT and name.lower() != "index.html":
            shutil.copy2(full, os.path.join(dst, name))
            files.append(f'<li><a href="{urllib.parse.quote(name)}">📄 {html.escape(name)}</a></li>')
        elif name.lower() == "index.html":
            shutil.copy2(full, os.path.join(dst, "_index.html"))
            files.append(f'<li><a href="_index.html">📄 index.html</a></li>')
    if not dirs and not files:
        shutil.rmtree(dst, ignore_errors=True)
        return False
    title = label0 if len(rel_parts) == 1 else rel_parts[-1]
    write(os.path.join(dst, "index.html"),
          page(title, crumb(rel_parts, label0, False), f"<h1>{html.escape(title)}</h1><ul class='list'>{''.join(dirs + files)}</ul>"))
    return True


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    items = []
    for key, src, label in ROOTS:
        if build_dir(src, [key], label):
            items.append(f'<li><a href="{key}/index.html">📁 {html.escape(label)}</a></li>')
    write(os.path.join(OUT, "index.html"),
          page("Tài liệu Lab", "🏠 Trang chủ", f"<h1>Tài liệu Lab</h1><ul class='list'>{''.join(items)}</ul>"))
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    print("Built ->", OUT)


if __name__ == "__main__":
    main()
