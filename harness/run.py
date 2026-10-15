"""LinguaCheck runner.

Loads the demo app in every language at several phone widths, once clean and
once per seeded change, runs checks.js, and diffs each run against the clean
baseline for the same language and width. Writes results/raw.json and
results/summary.json, plus evidence screenshots.

Usage: python harness/run.py
"""
import functools
import http.server
import json
import pathlib
import re
import socketserver
import threading
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"
OUT = ROOT / "results"
SHOTS = OUT / "shots"

LANGS = ["en", "pseudo", "zh", "bn", "ta", "th"]
VIEWPORTS = [(320, 640), (360, 740), (412, 915)]
STRATEGIES = {
    "English only": ["en"],
    "English + pseudo-localisation": ["en", "pseudo"],
    "English + real languages": ["en", "zh", "bn", "ta", "th"],
}


def load_bug_ids():
    src = (APP / "bugs.js").read_text(encoding="utf-8")
    ids = re.findall(r"^\s*([DB]\d\d):\s*\{\s*kind:\s*\"(\w+)\",\s*title:\s*\"([^\"]+)\"", src, re.M)
    return [{"id": i, "kind": k, "title": t} for i, k, t in ids]


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(APP))
    handler.log_message = lambda *a, **k: None
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def main():
    OUT.mkdir(exist_ok=True)
    SHOTS.mkdir(exist_ok=True)
    checks = (ROOT / "harness" / "checks.js").read_text(encoding="utf-8")
    bugs = load_bug_ids()
    httpd, port = serve()
    base = f"http://127.0.0.1:{port}/index.html"
    raw = {}  # raw[bug or "clean"][lang][width] = findings
    t0 = time.time()
    runs = 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h in VIEWPORTS:
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
            page = ctx.new_page()
            for lang in LANGS:
                for bug in [None] + [b["id"] for b in bugs]:
                    url = f"{base}?ci=1&lang={lang}" + (f"&bug={bug}" if bug else "")
                    page.goto(url)
                    page.wait_for_selector("html[data-ready='1']")
                    page.evaluate("document.fonts.ready")
                    findings = page.evaluate(checks)
                    key = bug or "clean"
                    raw.setdefault(key, {}).setdefault(lang, {})[str(w)] = findings
                    runs += 1
            ctx.close()

        # Diff against the clean baseline.
        results = {}
        for b in bugs:
            per = {}
            for lang in LANGS:
                for w, _ in VIEWPORTS:
                    clean = {f["sig"] for f in raw["clean"][lang][str(w)]}
                    new = [f for f in raw[b["id"]][lang][str(w)] if f["sig"] not in clean]
                    if new:
                        per.setdefault(lang, {})[str(w)] = new
            results[b["id"]] = {**b, "flagged_in": per}

        # Evidence screenshots for each defect: English vs. first other language that flagged it.
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, device_scale_factor=2)
        page = ctx.new_page()
        for b in bugs:
            r = results[b["id"]]
            if b["kind"] != "defect" or not r["flagged_in"]:
                continue
            order = ["en"] + [l for l in ["ta", "bn", "th", "zh", "pseudo"] if l in r["flagged_in"]]
            show = [order[0]] + ([order[1]] if len(order) > 1 else [])
            target = None
            for lang in order:
                for w in ["360", "320", "412"]:
                    if lang in r["flagged_in"] and w in r["flagged_in"][lang]:
                        target = r["flagged_in"][lang][w][0]["target"]
                        break
                if target:
                    break
            shots = {}
            for lang in show:
                page.goto(f"{base}?ci=1&lang={lang}&bug={b['id']}")
                page.wait_for_selector("html[data-ready='1']")
                page.evaluate("document.fonts.ready")
                sel = f'[data-testid="{target}"]' if target and not target.startswith("#") else (target or "body")
                loc = page.locator(sel).first
                try:
                    box = loc.bounding_box()
                    if box and target not in ("body",):
                        page.evaluate("(y) => window.scrollTo(0, y)", 0)
                        box = page.evaluate(
                            "(s) => { const r = document.querySelector(s).getBoundingClientRect();"
                            " return {x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height}; }", sel)
                        pad = 28
                        clip = {"x": 0, "y": max(0, box["y"] - pad), "width": 360,
                                "height": min(box["h"] + 2 * pad, 320)}
                        fixed = page.evaluate(
                            "(s) => { let e = document.querySelector(s); for (; e; e = e.parentElement)"
                            " { if (getComputedStyle(e).position === 'fixed') return true; } return false; }", sel)
                        fn = SHOTS / f"{b['id']}_{lang}.png"
                        if fixed:
                            page.screenshot(path=str(fn), clip={"x": 0, "y": max(0, box["y"] - pad), "width": 360,
                                                                "height": min(740 - max(0, box["y"] - pad), 320)})
                        else:
                            page.screenshot(path=str(fn), clip=clip, full_page=True)
                        shots[lang] = f"shots/{fn.name}"
                except Exception as e:  # evidence is best-effort
                    shots[lang] = None
            r["shots"] = shots
        ctx.close()
        browser.close()
    httpd.shutdown()

    # Score each strategy.
    defects = [b for b in bugs if b["kind"] == "defect"]
    benign = [b for b in bugs if b["kind"] == "benign"]
    clean_total = {l: sum(len(raw["clean"][l][str(w)]) for w, _ in VIEWPORTS) for l in LANGS}
    scores = {}
    for name, langs in STRATEGIES.items():
        caught = [b["id"] for b in defects if any(l in results[b["id"]]["flagged_in"] for l in langs)]
        false_alarms = [b["id"] for b in benign if any(l in results[b["id"]]["flagged_in"] for l in langs)]
        scores[name] = {"languages": langs, "caught": caught, "caught_n": len(caught), "defects_n": len(defects),
                        "false_alarms": false_alarms, "false_alarm_n": len(false_alarms), "benign_n": len(benign),
                        "page_loads_per_release": len(langs) * len(VIEWPORTS)}
    per_lang = {l: sum(1 for b in defects if l in results[b["id"]]["flagged_in"]) for l in LANGS}
    only_real = [b["id"] for b in defects
                 if not any(l in results[b["id"]]["flagged_in"] for l in ["en", "pseudo"])
                 and any(l in results[b["id"]]["flagged_in"] for l in ["zh", "bn", "ta", "th"])]
    missed_all = [b["id"] for b in defects if not results[b["id"]]["flagged_in"]]

    summary = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "runs": runs, "seconds": round(time.time() - t0, 1),
        "languages": LANGS, "viewports": [w for w, _ in VIEWPORTS],
        "clean_baseline_findings": clean_total,
        "scores": scores, "per_language_catches": per_lang,
        "caught_only_by_real_languages": only_real, "missed_by_everything": missed_all,
        "bugs": results,
    }
    (OUT / "raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "bugs"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
