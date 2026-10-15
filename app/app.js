// Demo booking flow. All text is inserted with textContent, never as HTML,
// and URL parameters are checked against fixed allowlists, so nothing a
// visitor puts in the address bar can inject markup or script.
(function () {
  "use strict";
  const own = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);
  const params = new URLSearchParams(location.search);

  const LANGS = ["en", "zh", "bn", "ta", "th", "pseudo"];
  const reqLang = params.get("lang");
  const lang = LANGS.includes(reqLang) ? reqLang : "en";
  const reqBug = params.get("bug");
  const bugId = reqBug && /^[DB]\d\d$/.test(reqBug) && own(window.BUGS, reqBug) ? reqBug : null;
  const ci = params.get("ci") === "1"; // test runs hide the explainer panel

  const T = window.I18N[lang];
  document.documentElement.lang = lang === "pseudo" ? "en-XA" : lang;

  const go = (changes) => {
    const p = new URLSearchParams();
    const next = { lang, bug: bugId, ...changes };
    if (next.lang && next.lang !== "en") p.set("lang", next.lang);
    if (next.bug) p.set("bug", next.bug);
    if (ci) p.set("ci", "1");
    const q = p.toString();
    location.search = q ? "?" + q : "";
  };

  const langSelect = document.getElementById("lang-select");
  langSelect.value = lang;
  langSelect.addEventListener("change", (e) => go({ lang: e.target.value }));

  const el = (tag, cls, text, attrs) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    if (attrs) for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    return n;
  };
  const get = (key) => key.split(".").reduce((o, k) => (o != null && own(o, k) ? o[k] : ""), T);

  // Facility cards
  const facilities = [
    { key: "fac_badminton", isNew: false },
    { key: "fac_football", isNew: true },
    { key: "fac_computer", isNew: false }
  ];
  const cards = document.getElementById("cards");
  facilities.forEach((f, i) => {
    const c = el("div", "card" + (i === 0 ? " selected" : ""), null, { "data-testid": "card-" + i });
    const title = el("div", "title", null, { "data-testid": "card-title-" + i });
    title.appendChild(el("span", "name", T[f.key]));
    if (f.isNew) title.appendChild(el("span", "badge-new", T.new_badge, { "data-testid": "badge-new" }));
    const side = el("div", "side");
    side.appendChild(el("span", "status", T.available, { "data-testid": "status-" + i }));
    side.appendChild(el("span", "price", T.price, { "data-testid": "price-" + i }));
    c.append(title, side, el("div", "desc", T.fac_desc, { "data-testid": "desc-" + i }));
    cards.appendChild(c);
  });

  // Day chips
  const days = document.getElementById("days");
  T.days.forEach((d, i) => {
    days.appendChild(el("button", "chip", d, { "data-testid": "day-" + i, "aria-pressed": i === 2 ? "true" : "false" }));
  });

  // Time slots
  const times = ["8:00–10:00", "14:00–16:00", "18:00–20:00", "20:00–22:00"];
  const slots = document.getElementById("slots");
  T.slots.forEach((s, i) => {
    const b = el("button", "slot", null, { "data-testid": "slot-" + i, "aria-pressed": i === 2 ? "true" : "false" });
    b.append(el("span", null, s), el("small", null, times[i]));
    slots.appendChild(b);
  });

  // Simple selection behaviour so the demo feels real
  const toggleGroup = (container) => container.addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    container.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b === btn ? "true" : "false"));
    const i = Number(btn.dataset.testid.split("-")[1]);
    if (container === days) document.getElementById("sum-date").textContent = T.days[i];
    if (container === slots) document.getElementById("sum-time").textContent = T.slots[i] + " · " + times[i];
  });
  toggleGroup(days);
  toggleGroup(slots);

  document.getElementById("sum-fac").textContent = T.fac_badminton;
  document.getElementById("sum-date").textContent = T.days[2];
  document.getElementById("sum-time").textContent = T.slots[2] + " · " + times[2];

  document.querySelectorAll("[data-i18n]").forEach((n) => { n.textContent = get(n.dataset.i18n); });
  document.getElementById("name").placeholder = T.name_placeholder;

  // Demo controls (hidden during automated test runs)
  const ctl = document.getElementById("democtl");
  if (ci) {
    ctl.remove();
  } else {
    const sel = document.getElementById("ctl-bug");
    sel.appendChild(el("option", null, "None (clean app)", { value: "" }));
    const groups = { defect: el("optgroup", null, null, { label: "Seeded defects" }), benign: el("optgroup", null, null, { label: "Harmless changes" }) };
    for (const [id, b] of Object.entries(window.BUGS)) {
      groups[b.kind].appendChild(el("option", null, id + " · " + b.title, { value: id }));
    }
    sel.append(groups.defect, groups.benign);
    sel.value = bugId || "";
    sel.addEventListener("change", (e) => go({ bug: e.target.value || null }));
    const note = document.getElementById("ctl-note");
    note.textContent = bugId
      ? (window.BUGS[bugId].kind === "defect"
        ? "Defect applied. Try English, then Tamil or Pseudo, and compare."
        : "Harmless change applied. The tests should not flag this.")
      : "No change applied. This is the clean baseline.";
  }

  // Apply the seeded change last
  if (bugId) {
    const bug = window.BUGS[bugId];
    if (bug.css) document.getElementById("bug-style").textContent = bug.css;
    if (bug.js) bug.js(document);
  }
  document.documentElement.dataset.ready = "1";
})();
