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
CUTS = {"full": "Full video", "short": "Short", "phone": "Phone"}
FONTS = ("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600&family=Inter:wght@400;500;600"
         "&family=JetBrains+Mono:wght@400;500&display=swap")
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' "
           "height='32' rx='8' fill='%236A1B9A'/%3E%3Cpath d='M12.5 9.5v13l10-6.5z' fill='%23FCFBFD'/%3E%3C/svg%3E")
ARROW = '<svg class="ext" viewBox="0 0 12 12" aria-hidden="true"><path d="M3.5 8.5l5-5M4.5 3.5h4v4"/></svg>'


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
<meta name="theme-color" content="#FCFBFD" media="(prefers-color-scheme: light)" />
<meta name="theme-color" content="#131117" media="(prefers-color-scheme: dark)" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link rel="stylesheet" href="{FONTS}" />
<link rel="icon" href="{FAVICON}" />
<link rel="stylesheet" href="{root}{asset("style.css")}" />
</head>"""


def footer(site: dict) -> str:
    return f"""  <footer class="site">
    <span>&copy; 2026 <a href="{e(site["owner_url"])}">{e(site["owner"])}</a></span>
    <span>Narration voices generated with <a href="https://elevenlabs.io" target="_blank" rel="noopener">ElevenLabs</a>.</span>
  </footer>"""


def card(p: dict) -> str:
    v, slug = p["videos"], p["slug"]
    cuts = "".join(f'<li><a href="{slug}/#{c}">{CUTS[c]} <span>{clock(v[c]["seconds"])}</span></a></li>'
                   for c in CUTS if c in v)
    preview = (f'<video muted loop playsinline preload="none" data-src="{e(v["short"]["src"])}" '
               f'aria-hidden="true" tabindex="-1"></video>') if "short" in v else ""
    return f"""    <article class="card">
      <a class="thumb" href="{slug}/" aria-label="Watch: {e(p["name"])}">
        <img src="{e(v["full"]["poster"])}" alt="" width="1280" height="720" loading="lazy" />
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
    cards = "\n".join(card(p) for p in papers)
    return f"""{head(f'{site["title"]} · {site["owner"]}', site["intro"], site["url"], site["url"] + "assets/og.jpg", "")}
<body class="home">
<div class="wrap">
  <header class="masthead">
    <p class="eyebrow"><a href="{e(site["owner_url"])}">{e(site["owner"])}</a></p>
    <h1>{e(site["title"])}</h1>
    <p class="intro">{e(site["intro"])}</p>
    <p class="stats">{len(papers)} papers · {len(videos)} videos · {minutes} minutes</p>
  </header>
  <main class="grid">
{cards}
  </main>
{footer(site)}
</div>
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
<div class="wrap narrow">
  <nav class="crumbs"><a href="../">&larr; {e(site["title"])}</a></nav>
  <header class="paper-head">
    <p class="meta">{e(p["venue"])} · {p["year"]}</p>
    <h1>{e(p["title"])}</h1>
    <p class="authors">{e(", ".join(p["authors"]))}</p>
    <ul class="links">{links}</ul>
  </header>
  <main>
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
    <pre class="bib" id="bib">{e(p["bibtex"])}</pre>
  </section>
  </main>
  <nav class="pager" aria-label="More papers">{prev}{nxt}</nav>
{footer(site)}
</div>
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
