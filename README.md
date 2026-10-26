# Video Library

Narrated explainers of research papers: https://daravaram.github.io/video-library/

Each paper comes in three cuts: the full video, a one-minute short (16:9) and a 90-second phone video (9:16, with
its captions burned in). Each paper has its own page with the three cuts, the chapters of the full video, the
abstract, links to the paper and its code, and a BibTeX entry.

## Adding a paper

1. Put its files in `videos/<slug>/`: `full.mp4`, `short.mp4` and `phone.mp4`, a poster for each (`full.jpg`,
   `short.jpg`, `phone.jpg`), and captions for the 16:9 cuts (`full.vtt`, `short.vtt`).
2. Add an entry to `papers.json`: title, authors, venue, links, abstract, BibTeX and the full video's chapters. The
   order of `papers` is the order on the page.
3. Run `python3 build.py` (standard library only) and commit the generated pages with the videos.

A video can also play from another site: the full PCD and FedPCD videos play from their project pages. Give its
URL as `src` and its length in seconds as `seconds`; a local video's length is read from the file.

GitHub Pages serves the `main` branch as it is (`.nojekyll`, no build on GitHub). GitHub refuses files over
100 MB and warns above 50 MB. The pages use the reader's system fonts. One external request: a hidden visitor-map counter
(visitormap.workers.dev) on every page.
