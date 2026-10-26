#!/usr/bin/env python3
"""Builds the video library from papers.json: index.html, and one page per paper in <slug>/index.html.

    python3 build.py

Standard library only. Every local file papers.json names must exist. A local video's length is read from its
MP4 header; a video played from another site (the full PCD and FedPCD videos, from their project pages) gives
its length in papers.json as "seconds".
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CUTS = {"full": "Full Video", "short": "Short", "phone": "Phone"}
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cdefs%3E%3ClinearGradient "
           "id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0' stop-color='%237C3AED'/%3E%3Cstop offset='1' "
           "stop-color='%2306B6D4'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='32' height='32' rx='8' "
           "fill='url(%23g)'/%3E%3Cpath d='M12.5 9.5v13l10-6.5z' fill='%23FFFFFF'/%3E%3C/svg%3E")
CHEVRON = ('<svg class="chevron" viewBox="0 0 9 14" aria-hidden="true"><path d="M7.5 1.5 2 7l5.5 5.5"/></svg>')
ARROW = '<svg class="ext" viewBox="0 0 12 12" aria-hidden="true"><path d="M3.5 8.5l5-5M4.5 3.5h4v4"/></svg>'
# the visitor map, as on the PCD and FedPCD pages: rendered (so the visit is logged) but invisible
VISITOR_MAP = """<div class="visitor-widget" aria-hidden="true">
<script type="text/javascript" id="mapmyvisitors" src="https://visitormap.visitormap.workers.dev/map.js?d=vQcILETVswZfTonNsgaogfZ0&cl=171221&co=0e0b13&ct=a79bbd&w=a"></script>
</div>"""


def e(text) -> str:
    return html.escape(str(text), quote=True)


def asset(name: str) -> str:
    """assets/<name> with its content hash, so a changed file isn't served from a browser's cache."""
    return f"assets/{name}?v={hashlib.sha1((HERE / 'assets' / name).read_bytes()).hexdigest()[:8]}"


def remote(src: str) -> bool:
    return src.startswith(("http://", "https://"))


def mp4_seconds(path: Path) -> float:
    """The movie's length from the mvhd box of an MP4."""
    data = path.read_bytes()
    i = data.find(b"mvhd")
    if i < 0:
        sys.exit(f"no mvhd box in {path}")
    if data[i + 4] == 1:
        scale, length = struct.unpack(">IQ", data[i + 24:i + 36])
    else:
        scale, length = struct.unpack(">II", data[i + 16:i + 24])
    return length / scale


def clock(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"


def chapter_seconds(stamp: str) -> int:
    m, s = stamp.split(":")
    return int(m) * 60 + int(s)


def linkify(text: str) -> str:
    return re.sub(r"(https?://[^\s<]+)", r'<a href="\1" target="_blank" rel="noopener">\1</a>', e(text))


def summary(text: str, limit: int = 158) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def load() -> dict:
    lib = json.loads((HERE / "papers.json").read_text(encoding="utf-8"))
    missing = []
    for p in lib["papers"]:
        for cut, v in p["videos"].items():
            for key in ("src", "captions", "poster"):
                if key in v and not remote(v[key]) and not (HERE / v[key]).is_file():
                    missing.append(v[key])
            if "seconds" not in v:
                v["seconds"] = mp4_seconds(HERE / v["src"]) if not remote(v["src"]) else None
            if v["seconds"] is None:
                sys.exit(f'{p["slug"]} {cut}: a video from another site needs "seconds" in papers.json')
    if missing:
        sys.exit("missing files:\n  " + "\n  ".join(missing))
    return lib


def head(title: str, description: str, url: str, image: str, root: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{e(title)}</title>
<meta name="description" content="{e(description)}" />
<link rel="canonical" href="{e(url)}" />
<meta property="og:type" content="website" />
<meta property="og:title" content="{e(title)}" />
<meta property="og:description" content="{e(description)}" />
<meta property="og:url" content="{e(url)}" />
<meta property="og:image" content="{e(image)}" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="theme-color" content="#F7F6FB" media="(prefers-color-scheme: light)" />
<meta name="theme-color" content="#0C0B12" media="(prefers-color-scheme: dark)" />
<link rel="icon" href="{FAVICON}" />
<link rel="stylesheet" href="{root}{asset("style.css")}" />
</head>"""


def footer(site: dict) -> str:
    return f"""  <footer class="site">
    <span>&copy; 2026 <a href="{e(site["owner_url"])}">{e(site["owner"])}</a></span>
    <span>Narration voices generated with <a href="https://elevenlabs.io" target="_blank" rel="noopener" translate="no">ElevenLabs</a>.</span>
  </footer>"""


def card(p: dict, i: int) -> str:
    v, slug = p["videos"], p["slug"]
    cuts = "".join(f'<li><a href="{slug}/#{c}">{CUTS[c]} <span>{clock(v[c]["seconds"])}</span></a></li>'
                   for c in CUTS if c in v)
    preview = (f'<video muted loop playsinline preload="none" data-src="{e(v["short"]["src"])}" '
               f'aria-hidden="true" tabindex="-1"></video>') if "short" in v else ""
    # the first row is above the fold on a wide screen: load it now, the first one first
    load = 'fetchpriority="high"' if i == 0 else "" if i == 1 else 'loading="lazy"'
    return f"""    <article class="card">
      <a class="thumb" href="{slug}/" aria-label="Watch: {e(p["name"])}">
        <img src="{e(v["full"]["poster"])}" alt="" width="1280" height="720" {load} />
        {preview}
        <span class="runtime">{clock(v["full"]["seconds"])}</span>
      </a>
      <p class="meta">{e(p["venue_short"])} · {p["year"]}</p>
      <h2><a href="{slug}/">{e(p["title"])}</a></h2>
      <p class="authors">{e(", ".join(p["authors"]))}</p>
      <ul class="cuts" aria-label="Cuts">{cuts}</ul>
    </article>"""


def index(lib: dict) -> str:
    site, papers = lib["site"], lib["papers"]
    videos = [v for p in papers for v in p["videos"].values()]
    minutes = round(sum(v["seconds"] for v in videos) / 60)
    cards = "\n".join(card(p, i) for i, p in enumerate(papers))
    return f"""{head(f'{site["title"]} · {site["owner"]}', site["intro"], site["url"], site["url"] + "assets/og.jpg", "")}
<body class="home">
<a class="skip" href="#main">Skip to Content</a>
<div class="bar">
  <div class="wrap bar-inner"><span class="bar-title" aria-hidden="true">{e(site["title"])}</span></div>
</div>
<div class="wrap">
  <header class="masthead">
    <p class="eyebrow"><a href="{e(site["owner_url"])}">{e(site["owner"])}</a></p>
    <h1>{e(site["title"])}</h1>
    <p class="intro">{e(site["intro"])}</p>
    <p class="stats">{len(papers)} papers · {len(videos)} videos · {minutes} minutes</p>
  </header>
  <main class="grid" id="main">
{cards}
  </main>
{footer(site)}
</div>
{VISITOR_MAP}
<script src="{asset("library.js")}"></script>
</body>
</html>
"""


def screen(cut: str, v: dict, root: str) -> str:
    def at(path: str) -> str:
        return path if remote(path) else root + path

    portrait = cut == "phone"
    cors = ' crossorigin="anonymous"' if remote(v.get("captions", "")) else ""
    track = (f'\n        <track kind="captions" src="{e(at(v["captions"]))}" srclang="en" label="English" />'
             if "captions" in v else "")
    label = f'{CUTS[cut]}, {clock(v["seconds"])}' + (", captions burned in" if portrait else "")
    return f"""      <div class="screen{" portrait" if portrait else ""}" data-cut="{cut}"{"" if cut == "full" else " hidden"}>
        <video controls playsinline preload="{"metadata" if cut == "full" else "none"}"{cors} poster="{e(at(v["poster"]))}" aria-label="{e(label)}">
        <source src="{e(at(v["src"]))}" type="video/mp4" />{track}
        </video>
      </div>"""


def page(lib: dict, i: int) -> str:
    site, papers = lib["site"], lib["papers"]
    p = papers[i]
    v = p["videos"]
    url = site["url"] + p["slug"] + "/"
    tabs = "".join(f'<button type="button" data-cut="{c}" aria-pressed="{"true" if c == "full" else "false"}">'
                   f'{CUTS[c]} <span>{clock(v[c]["seconds"])}</span></button>' for c in CUTS if c in v)
    screens = "\n".join(screen(c, v[c], "../") for c in CUTS if c in v)
    links = "".join(f'<li><a href="{e(l["url"])}" target="_blank" rel="noopener">{e(l["label"])}{ARROW}</a></li>'
                    for l in p["links"])
    chapters = ""
    if p["chapters"]:
        items = "".join(f'<li><button type="button" data-t="{chapter_seconds(t)}"><time>{e(t)}</time>{e(name)}</button></li>'
                        for t, name in p["chapters"])
        chapters = f'\n    <ol class="chapters" aria-label="Chapters of the full video">{items}</ol>'
    prev = (f'<a class="prev" href="../{papers[i - 1]["slug"]}/"><small>Previous</small>'
            f'<span>{e(papers[i - 1]["name"])}</span></a>') if i > 0 else ""
    nxt = (f'<a class="next" href="../{papers[i + 1]["slug"]}/"><small>Next</small>'
           f'<span>{e(papers[i + 1]["name"])}</span></a>') if i + 1 < len(papers) else ""
    image = site["url"] + v["full"]["poster"]
    return f"""{head(f'{p["name"]} · {site["title"]}', summary(p["abstract"]), url, image, "../")}
<body class="paper">
<a class="skip" href="#main">Skip to Content</a>
<div class="bar">
  <div class="wrap narrow bar-inner">
    <nav class="crumbs" aria-label="Breadcrumb"><a href="../">{CHEVRON}{e(site["title"])}</a></nav>
    <span class="bar-title" aria-hidden="true">{e(p["name"])}</span>
  </div>
</div>
<div class="wrap narrow">
  <header class="paper-head">
    <p class="meta">{e(p["venue"])} · {p["year"]}</p>
    <h1>{e(p["title"])}</h1>
    <p class="authors">{e(", ".join(p["authors"]))}</p>
    <ul class="links">{links}</ul>
  </header>
  <main id="main">
  <section class="watch" aria-label="Videos">
    <div class="seg" role="group" aria-label="Which cut">{tabs}</div>
    <div class="stage">
{screens}
    </div>{chapters}
  </section>
  <section class="block">
    <h2 class="label">Abstract</h2>
    <p class="abstract">{linkify(p["abstract"])}</p>
  </section>
  <section class="block">
    <div class="label-row"><h2 class="label">Cite</h2><button class="copy" type="button" data-target="bib">Copy BibTeX</button></div>
    <pre class="bib" id="bib" translate="no">{e(p["bibtex"])}</pre>
    <p class="visually-hidden" id="copy-status" role="status" aria-live="polite"></p>
  </section>
  </main>
  <nav class="pager" aria-label="More papers">{prev}{nxt}</nav>
{footer(site)}
</div>
{VISITOR_MAP}
<script src="../{asset("library.js")}"></script>
</body>
</html>
"""


def main() -> None:
    lib = load()
    (HERE / "index.html").write_text(index(lib), encoding="utf-8")
    for i, p in enumerate(lib["papers"]):
        out = HERE / p["slug"] / "index.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(page(lib, i), encoding="utf-8")
    print(f'wrote index.html and {len(lib["papers"])} paper pages')


if __name__ == "__main__":
    main()
