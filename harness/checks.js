// LinguaCheck layout + accessibility checks.
// Runs inside the page and returns a list of findings. Each finding has a
// stable signature (check type + nearest data-testid) so a run can be diffed
// against a clean baseline for the same language and screen size.
(() => {
  const TOL = 1.5; // px tolerance for sub-pixel rounding
  const vw = window.innerWidth;
  const findings = [];
  const seen = new Set();

  const tidOf = (el) => {
    let e = el;
    while (e && e !== document.body) {
      if (e.dataset && e.dataset.testid) return e.dataset.testid;
      if (e.id) return "#" + e.id;
      e = e.parentElement;
    }
    return "body";
  };
  const add = (type, el, detail) => {
    const sig = type + "@" + tidOf(el);
    if (seen.has(sig)) return;
    seen.add(sig);
    const r = el.getBoundingClientRect();
    findings.push({ sig, type, target: tidOf(el), detail,
      box: { x: r.left + window.scrollX, y: r.top + window.scrollY, w: r.width, h: r.height } });
  };

  const visible = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden" || +cs.opacity === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };

  // Text leaves: elements that directly own non-empty text.
  const leaves = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const t = walker.currentNode;
    if (!t.nodeValue.trim()) continue;
    const el = t.parentElement;
    if (!el || ["SCRIPT", "STYLE", "OPTION", "SELECT"].includes(el.tagName)) continue;
    if (!visible(el)) continue;
    const range = document.createRange();
    range.selectNodeContents(t);
    const rects = [...range.getClientRects()].filter((r) => r.width > 0 && r.height > 0);
    if (!rects.length) continue;
    const u = rects.reduce((a, r) => ({ l: Math.min(a.l, r.left), t: Math.min(a.t, r.top), r: Math.max(a.r, r.right), b: Math.max(a.b, r.bottom) }),
      { l: Infinity, t: Infinity, r: -Infinity, b: -Infinity });
    leaves.push({ el, rect: u });
  }

  const isFixed = (el) => {
    for (let e = el; e && e !== document.body; e = e.parentElement) {
      const p = getComputedStyle(e).position;
      if (p === "fixed" || p === "sticky") return e;
    }
    return null;
  };

  // 1. Clipped text: text extends beyond an ancestor that hides overflow.
  for (const { el, rect } of leaves) {
    for (let a = el; a && a !== document.body; a = a.parentElement) {
      const cs = getComputedStyle(a);
      const ox = cs.overflowX !== "visible", oy = cs.overflowY !== "visible";
      if (!ox && !oy) continue;
      const ar = a.getBoundingClientRect();
      const left = ar.left + a.clientLeft, top = ar.top + a.clientTop;
      const right = left + a.clientWidth, bottom = top + a.clientHeight;
      if (ox && (rect.r > right + TOL || rect.l < left - TOL)) { add("clipped-x", el, "text wider than its container"); break; }
      if (oy && (rect.b > bottom + TOL || rect.t < top - TOL)) { add("clipped-y", el, "text taller than its container"); break; }
    }
    // 2. Off-screen text.
    if (rect.r > vw + TOL || rect.l < -TOL) add("offscreen", el, "text runs past the screen edge");
  }

  // 3. Whole page scrolls sideways.
  if (document.documentElement.scrollWidth > vw + TOL) add("page-hscroll", document.body, "page wider than the screen");

  // 4. Overlaps between text and controls in normal flow.
  const controls = [...document.querySelectorAll("button, input, select, a[href]")].filter(visible);
  const boxes = [
    ...leaves.map(({ el, rect }) => ({ el, l: rect.l, t: rect.t, r: rect.r, b: rect.b })),
    ...controls.map((el) => { const r = el.getBoundingClientRect(); return { el, l: r.left, t: r.top, r: r.right, b: r.bottom }; })
  ].map((b) => ({ ...b, root: isFixed(b.el) }));
  // v2: compare items that share the same layer (normal flow, or the same
  // fixed bar). v1 skipped fixed bars entirely and so missed overlaps inside
  // the bottom tab bar (seeded defect D15).
  for (let i = 0; i < boxes.length; i++) {
    for (let j = i + 1; j < boxes.length; j++) {
      const A = boxes[i], B = boxes[j];
      if (A.root !== B.root) continue;
      if (A.el === B.el || A.el.contains(B.el) || B.el.contains(A.el)) continue;
      const w = Math.min(A.r, B.r) - Math.max(A.l, B.l);
      const h = Math.min(A.b, B.b) - Math.max(A.t, B.t);
      if (w > 2 && h > 2) { add("overlap", A.el, "overlaps " + tidOf(B.el)); }
    }
  }

  // 5. Content hidden behind fixed bars when scrolled to the very bottom.
  window.scrollTo(0, document.documentElement.scrollHeight);
  const fixedBars = [...document.querySelectorAll("body *")].filter((e) => getComputedStyle(e).position === "fixed" && visible(e));
  const flow = [...document.querySelectorAll("main *")].filter((e) => visible(e) && !isFixed(e) &&
    (e.matches("button, input, select") || [...e.childNodes].some((n) => n.nodeType === 3 && n.nodeValue.trim())));
  for (const bar of fixedBars) {
    const br = bar.getBoundingClientRect();
    for (const e of flow) {
      const r = e.getBoundingClientRect();
      const w = Math.min(r.right, br.right) - Math.max(r.left, br.left);
      const h = Math.min(r.bottom, br.bottom) - Math.max(r.top, br.top);
      if (w > 2 && h > 2) add("covered", e, "hidden behind " + tidOf(bar));
    }
  }
  window.scrollTo(0, 0);

  // 6. Accessibility basics.
  const nameOf = (el) => {
    if (el.getAttribute("aria-label")) return el.getAttribute("aria-label");
    const lb = el.getAttribute("aria-labelledby");
    if (lb) return lb.split(/\s+/).map((id) => (document.getElementById(id) || {}).textContent || "").join(" ");
    if (el.id) { const l = document.querySelector('label[for="' + el.id + '"]'); if (l) return l.textContent; }
    if (el.tagName === "BUTTON") return el.textContent;
    return el.getAttribute("title") || "";
  };
  for (const el of controls) {
    if (!nameOf(el).trim()) add("no-accessible-name", el, "control has no accessible name");
    const r = el.getBoundingClientRect();
    if (r.height < 32 || r.width < 32) add("small-target", el, `touch target ${Math.round(r.width)}×${Math.round(r.height)}px`);
  }

  const parse = (c) => { const m = c.match(/[\d.]+/g); return m ? m.map(Number) : [0, 0, 0, 0]; };
  const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const bgOf = (el) => {
    for (let e = el; e; e = e.parentElement) {
      const c = parse(getComputedStyle(e).backgroundColor);
      if (c.length < 4 ? true : c[3] > 0.5) { if (getComputedStyle(e).backgroundColor !== "rgba(0, 0, 0, 0)") return c; }
    }
    return [255, 255, 255];
  };
  for (const { el } of leaves) {
    const cs = getComputedStyle(el);
    const size = parseFloat(cs.fontSize);
    if (size < 12) add("tiny-text", el, `font-size ${size}px`);
    const fg = parse(cs.color), bg = bgOf(el);
    const L1 = lum(fg), L2 = lum(bg);
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const large = size >= 24 || (size >= 18.66 && +cs.fontWeight >= 700);
    if (ratio < (large ? 3 : 4.5)) add("low-contrast", el, `contrast ${ratio.toFixed(2)}:1`);
  }

  return findings;
})();
