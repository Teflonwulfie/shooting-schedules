#!/usr/bin/env python3
"""Add or update one page on the site.

Usage:  python3 tools/publish.py /path/to/file.html [more files...]

Each input is a file saved by the Ad Multiplier app:
  "Download filming page"  ->  <PREFIX>_shooting_schedule.html  ->  <prefix>.html
  "Download copy page"     ->  <PREFIX>_primary_copy.html       ->  <prefix>-copy.html

The file is copied to the site root, search engines are told not to index it,
schedules.json is updated and index.html is rebuilt. A product with both pages
shows both buttons on the index.
"""
import datetime
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOINDEX = '<meta name="robots" content="noindex,nofollow">'


def read_data(page: str) -> dict:
    m = re.search(r"var D=(\{.*?\});\s*\nvar KEY", page, re.S)
    if not m:
        sys.exit("This does not look like a page saved by the Ad Multiplier app.")
    return json.loads(m.group(1))


def slug_for(code: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", code.lower()).strip("-")
    if not s or s in ("index", "schedules") or s.endswith("-copy"):
        sys.exit("The project's file prefix cannot be used as a page name: %r" % code)
    return s


def load_items() -> list:
    path = ROOT / "schedules.json"
    items = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    out = []
    for it in items:
        if "film" not in it and "copy" not in it:  # first layout: filming pages only
            it = {"slug": it["slug"], "name": it["name"], "updated": it["updated"], "updated_label": it["updated_label"],
                  "film": {"total": it["total"], "clips": it["clips"], "time": it["time"]}, "copy": None}
        out.append(it)
    return out


def plural(n: int, word: str) -> str:
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def build_index(items: list) -> str:
    cards = []
    for it in sorted(items, key=lambda x: x["updated"], reverse=True):
        lines, links = [], []
        film, copy = it.get("film"), it.get("copy")
        if film:
            lines.append("%s total ads &middot; %s &middot; about %s of filming" % (film["total"], plural(film["clips"], "clip"), html.escape(film["time"])))
            links.append('<a class="btn primary" href="%s.html">Filming schedule</a>' % it["slug"])
        if copy:
            lines.append("%s of primary copy" % plural(copy["sets"], "ad"))
            links.append('<a class="btn" href="%s-copy.html">Primary copy</a>' % it["slug"])
        cards.append(
            '<section class="card"><b>%s</b>%s<span class="when">Updated %s</span><div class="row">%s</div></section>'
            % (html.escape(it["name"]), "".join("<span>%s</span>" % x for x in lines), html.escape(it["updated_label"]), "".join(links))
        )
    body = "\n".join(cards) if cards else '<p class="empty">Nothing published yet.</p>'
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
%s
<title>Shooting schedules and ad copy</title>
<style>
body{margin:0;background:#eef1f3;color:#141a20;font:400 16px/1.5 "Segoe UI",system-ui,-apple-system,sans-serif}
.hdr{background:#141a20;color:#f3f5f6;padding:22px 16px}
.in{max-width:760px;margin:0 auto}
h1{margin:0;font-size:26px;font-weight:800}
.hdr p{margin:6px 0 0;color:#a3aeb8}
main{padding:18px 16px 60px}
.card{display:flex;flex-direction:column;gap:2px;background:#fff;border:1px solid #cdd5db;border-left:5px solid #f0bf2c;border-radius:8px;padding:14px 16px;margin-bottom:12px}
.card b{font-size:19px}
.card span{color:#55616d}
.card .when{font-size:13px}
.row{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.btn{display:inline-block;border:1px solid #141a20;border-radius:6px;padding:8px 14px;font-weight:600;color:#141a20;text-decoration:none;background:#fff}
.btn.primary{background:#f0bf2c;border-color:#f0bf2c;color:#1a1503}
.btn:hover,.btn:focus-visible{outline:2px solid #1d6fd6;outline-offset:2px}
.empty{color:#55616d}
</style>
</head>
<body>
<div class="hdr"><div class="in"><h1>Shooting schedules and ad copy</h1><p>Pick a product. Filming schedule opens the clips to film, with Start filming. Primary copy opens the written ads to copy or download.</p></div></div>
<main><div class="in">
%s
</div></main>
</body>
</html>
""" % (NOINDEX, body)


def publish_one(src: pathlib.Path, items: list) -> str:
    page = src.read_text(encoding="utf-8")
    data = read_data(page)
    slug = slug_for(str(data.get("code", "")))
    kind = "copy" if data.get("kind") == "copy" else "film"
    if "noindex" not in page:
        page = page.replace("<title>", NOINDEX + "\n<title>", 1)
    target = slug + ("-copy.html" if kind == "copy" else ".html")
    (ROOT / target).write_text(page, encoding="utf-8")

    now = datetime.datetime.now(datetime.timezone.utc)
    entry = next((x for x in items if x.get("slug") == slug), None)
    if entry is None:
        entry = {"slug": slug, "name": "", "updated": "", "updated_label": "", "film": None, "copy": None}
        items.append(entry)
    entry["name"] = str(data.get("name", slug))
    entry["updated"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    entry["updated_label"] = now.strftime("%d %b %Y").lstrip("0")
    if kind == "copy":
        entry["copy"] = {"sets": len(data.get("sets", []))}
        return "Published %s primary copy as %s (%s)" % (entry["name"], target, plural(entry["copy"]["sets"], "ad"))
    entry["film"] = {"total": int(data.get("total", 0)), "clips": sum(len(g.get("clips", [])) for g in data.get("groups", [])), "time": str(data.get("time", ""))}
    return "Published %s filming schedule as %s (%s total ads, %s)" % (entry["name"], target, entry["film"]["total"], plural(entry["film"]["clips"], "clip"))


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    items = load_items()
    for arg in sys.argv[1:]:
        print(publish_one(pathlib.Path(arg), items))
    (ROOT / "schedules.json").write_text(json.dumps(items, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "index.html").write_text(build_index(items), encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")


if __name__ == "__main__":
    main()
