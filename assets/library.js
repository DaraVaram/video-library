// Video Library. Every page: the bar's material appears once content scrolls under it, and its title once the
// page's own title has scrolled away. The index: a card's thumbnail plays its short, muted, while the pointer
// rests on it. A paper page: the cut switcher (its choice kept in the URL, #full, #short or #phone), the chapters
// of the full video, and the BibTeX copy button.
(() => {
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const pointer = matchMedia("(hover: hover) and (pointer: fine)").matches;

  const bar = document.querySelector(".bar");
  if (bar && "IntersectionObserver" in window) {
    const top = document.createElement("div");          // a pixel at the very top: out of view means scrolled
    top.setAttribute("aria-hidden", "true");
    top.style.cssText = "position:absolute;top:0;left:0;width:1px;height:1px;pointer-events:none";
    document.body.prepend(top);
    new IntersectionObserver(([e]) => bar.classList.toggle("scrolled", !e.isIntersecting)).observe(top);
    const title = document.querySelector("h1");
    new IntersectionObserver(([e]) => bar.classList.toggle("titled", !e.isIntersecting && e.boundingClientRect.top < 0),
      { rootMargin: `-${bar.offsetHeight}px 0px 0px 0px` }).observe(title);
  }

  if (pointer && !still) {
    document.querySelectorAll(".thumb").forEach((thumb) => {
      const video = thumb.querySelector("video");
      if (!video) return;
      let wait;
      thumb.addEventListener("mouseenter", () => {
        wait = setTimeout(() => {          // a pointer passing over starts no download
          if (!video.src) video.src = video.dataset.src;
          video.play().then(() => thumb.classList.add("playing")).catch(() => {});
        }, 220);
      });
      thumb.addEventListener("mouseleave", () => {
        clearTimeout(wait);
        thumb.classList.remove("playing");
        video.pause();
      });
    });
  }

  const seg = document.querySelector(".seg");
  if (seg) {
    const buttons = [...seg.querySelectorAll("button")];
    const screens = [...document.querySelectorAll(".screen")];
    const chapters = document.querySelector(".chapters");
    const cuts = buttons.map((b) => b.dataset.cut);
    const thumb = document.createElement("span");      // slides under the chosen cut
    thumb.className = "seg-thumb";
    thumb.setAttribute("aria-hidden", "true");
    seg.prepend(thumb);
    seg.classList.add("has-thumb");
    seg.style.setProperty("--n", buttons.length);

    const show = (cut, remember) => {
      if (!cuts.includes(cut)) cut = cuts[0];
      buttons.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.cut === cut)));
      seg.style.setProperty("--i", cuts.indexOf(cut));
      screens.forEach((s) => {
        const on = s.dataset.cut === cut;
        if (!on) s.querySelector("video").pause();
        s.hidden = !on;
      });
      if (chapters) chapters.hidden = cut !== "full";
      if (remember) history.replaceState(null, "", "#" + cut);
    };
    buttons.forEach((b) => b.addEventListener("click", () => show(b.dataset.cut, true)));
    addEventListener("hashchange", () => show(location.hash.slice(1)));
    show(location.hash.slice(1));
    requestAnimationFrame(() => requestAnimationFrame(() => seg.classList.add("ready")));

    if (chapters) {
      const video = document.querySelector('.screen[data-cut="full"] video');
      const items = [...chapters.querySelectorAll("button")];
      items.forEach((b) => b.addEventListener("click", () => {
        video.currentTime = Number(b.dataset.t);
        video.play().catch(() => {});
        video.scrollIntoView({ block: "nearest", behavior: still ? "auto" : "smooth" });
      }));
      video.addEventListener("timeupdate", () => {
        const now = video.currentTime + 0.25;
        const current = items.filter((b) => Number(b.dataset.t) <= now).pop();
        items.forEach((b) => b.classList.toggle("on", b === current));
      });
    }
  }

  const copy = document.querySelector(".copy");
  if (copy) {
    const label = copy.textContent;
    const status = document.getElementById("copy-status");   // read out by screen readers
    copy.addEventListener("click", async () => {
      const text = document.getElementById(copy.dataset.target).textContent;
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        const range = document.createRange();          // no clipboard access: select it for the reader
        range.selectNodeContents(document.getElementById(copy.dataset.target));
        getSelection().removeAllRanges();
        getSelection().addRange(range);
        if (status) status.textContent = "Couldn't copy automatically. The BibTeX is selected: press Ctrl+C or ⌘C to copy it.";
        return;
      }
      if (status) status.textContent = "BibTeX copied to the clipboard.";
      copy.textContent = "Copied";
      copy.classList.add("done");
      setTimeout(() => { copy.textContent = label; copy.classList.remove("done"); }, 1600);
    });
  }
})();
