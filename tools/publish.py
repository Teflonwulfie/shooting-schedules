#!/usr/bin/env python3
"""Add or update one shooting schedule on the site.

Usage:  python3 tools/publish.py /path/to/F1_shooting_schedule.html

The input is the file the Ad Multiplier app saves with "Download filming page".
This copies it to the site root as <prefix>.html, makes sure search engines are
told not to index it, records it in schedules.json and rebuilds index.html.
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
        sys.exit("This does not look like a filming page from the Ad Multiplier app.")
    return json.loads(m.group(1))


def slug_for(code: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", code.lower()).strip("-")
    if not s or s in ("index", "schedules"):
        sys.exit("The project's file prefix cannot be used as a page name: %r" % code)
    return s


def build_index(items: list) -> str:
    cards = []
    for it in sorted(items, key=lambda x: x["updated"], reverse=True):
        clips = "%d clip%s" % (it["clips"], "" if it["clips"] == 1 else "s")
        cards.append(
            '<a class="card" href="%s.html"><b>%s</b>'
            '<span>%s total ads &middot; %s &middot; about %s of filming</span>'
            '<span class="when">Updated %s</span></a>'
            % (it["slug"], html.escape(it["name"]), it["total"], clips, html.escape(it["time"]), html.escape(it["updated_label"]))
        )
    body = "\n".join(cards) if cards else '<p class="empty">Nothing published yet.</p>'
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
%s
<title>Shooting schedules</title>
<style>
body{margin:0;background:#eef1f3;color:#141a20;font:400 16px/1.5 "Segoe UI",system-ui,-apple-system,sans-serif}
.hdr{background:#141a20;color:#f3f5f6;padding:22px 16px}
.in{max-width:760px;margin:0 auto}
h1{margin:0;font-size:26px;font-weight:800}
.hdr p{margin:6px 0 0;color:#a3aeb8}
main{padding:18px 16px 60px}
.card{display:flex;flex-direction:column;gap:2px;background:#fff;border:1px solid #cdd5db;border-left:5px solid #f0bf2c;border-radius:8px;padding:14px 16px;margin-bottom:12px;color:inherit;text-decoration:none}
.card:hover,.card:focus-visible{border-color:#141a20;outline:none}
.card b{font-size:19px}
.card span{color:#55616d}
.card .when{font-size:13px}
.empty{color:#55616d}
</style>
</head>
<body>
<div class="hdr"><div class="in"><h1>Shooting schedules</h1><p>Pick a product, then press Start filming.</p></div></div>
<main><div class="in">
%s
</div></main>
</body>
</html>
""" % (NOINDEX, body)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = pathlib.Path(sys.argv[1])
    page = src.read_text(encoding="utf-8")
    data = read_data(page)
    slug = slug_for(str(data.get("code", "")))
    if "noindex" not in page:
        page = page.replace("<title>", NOINDEX + "\n<title>", 1)
    (ROOT / (slug + ".html")).write_text(page, encoding="utf-8")

    manifest_path = ROOT / "schedules.json"
    items = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    now = datetime.datetime.now(datetime.timezone.utc)
    entry = {
        "slug": slug,
        "name": str(data.get("name", slug)),
        "total": int(data.get("total", 0)),
        "clips": sum(len(g.get("clips", [])) for g in data.get("groups", [])),
        "time": str(data.get("time", "")),
        "updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_label": now.strftime("%d %b %Y").lstrip("0"),
    }
    items = [x for x in items if x.get("slug") != slug] + [entry]
    manifest_path.write_text(json.dumps(items, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "index.html").write_text(build_index(items), encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    print("Published %s as %s.html (%s total ads, %s clips)" % (entry["name"], slug, entry["total"], entry["clips"]))


if __name__ == "__main__":
    main()
