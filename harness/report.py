"""Build report/index.html from results/summary.json (self-contained, images inlined)."""
import base64
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
S = json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))
V1 = json.loads((ROOT / "results" / "summary_v1.json").read_text(encoding="utf-8")) if (ROOT / "results" / "summary_v1.json").exists() else None
LANG_NAMES = {"en": "English", "pseudo": "Pseudo", "zh": "Chinese", "bn": "Bengali", "ta": "Tamil", "th": "Thai"}
e = html.escape


def img(rel):
    if not rel:
        return ""
    p = ROOT / "results" / rel
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


def bars(items, maxv, unit=""):
    out = []
    for label, v, note in items:
        pct = 100 * v / maxv if maxv else 0
        out.append(f'<div class="bar"><div class="bl">{e(label)}</div><div class="bt"><div class="bf" style="width:{pct:.1f}%"></div></div>'
                   f'<div class="bv">{v}{unit}<span class="muted"> {e(note)}</span></div></div>')
    return "\n".join(out)


sc = S["scores"]
eng, pse, real = sc["English only"], sc["English + pseudo-localisation"], sc["English + real languages"]
nd, nb = eng["defects_n"], eng["benign_n"]
bugs = S["bugs"]
defects = [b for b in bugs.values() if b["kind"] == "defect"]
benign = [b for b in bugs.values() if b["kind"] == "benign"]
eng_missed = [b for b in defects if b["id"] not in eng["caught"] and b["flagged_in"]]

strategy_bars = bars([
    ("English only", eng["caught_n"], f"/ {nd} · {eng['page_loads_per_release']} page loads"),
    ("English + pseudo-localisation", pse["caught_n"], f"/ {nd} · {pse['page_loads_per_release']} page loads"),
    ("English + real languages", real["caught_n"], f"/ {nd} · {real['page_loads_per_release']} page loads"),
], nd)
lang_bars = bars([(LANG_NAMES[l], S["per_language_catches"][l], f"/ {nd}") for l in S["languages"]], nd)

rows = []
for b in defects + benign:
    cells = []
    for l in S["languages"]:
        ws = sorted(b["flagged_in"].get(l, {}).keys(), key=int)
        cells.append(f'<td class="{"hit" if ws else "miss"}" title="{e(", ".join(ws) + "px" if ws else "not flagged")}">{"●" if ws else "·"}<span class="sr">{"flagged" if ws else "not flagged"}</span></td>')
    kinds = sorted({f["type"] for l in b["flagged_in"].values() for w in l.values() for f in w})
    rows.append(f'<tr class="{b["kind"]}"><th scope="row"><code>{b["id"]}</code></th><td class="t">{e(b["title"])}</td>{"".join(cells)}<td class="k">{e(", ".join(kinds)) or "—"}</td></tr>')

gallery = []
for b in eng_missed:
    shots = b.get("shots") or {}
    figs = "".join(f'<figure><img src="{img(v)}" alt="{e(b["id"])} in {e(LANG_NAMES[k])}"><figcaption>{e(LANG_NAMES[k])}{" — passes" if k == "en" else " — flagged"}</figcaption></figure>'
                   for k, v in shots.items() if v)
    if figs:
        gallery.append(f'<div class="ev"><h3><code>{b["id"]}</code> {e(b["title"])}</h3><div class="pair">{figs}</div></div>')

v1_line = ""
if V1:
    v1s = V1["scores"]
    v1_line = (f"<li><b>The checker itself had a bug.</b> Version 1 skipped overlaps inside fixed bars, so it missed D15 (tab labels running into each other). "
               f"I fixed it after seeing the miss, which means the version 2 scores are slightly optimistic. Version 1 scores were "
               f"{v1s['English only']['caught_n']}, {v1s['English + pseudo-localisation']['caught_n']} and {v1s['English + real languages']['caught_n']} of {nd}.</li>")

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="no-referrer">
<title>LinguaCheck Results</title>
<style>
:root{{--bg:#f6f7f6;--card:#fff;--ink:#16201b;--muted:#56635c;--line:#d8dfdb;--accent:#0b6b57;--soft:#e1f0eb;--miss:#c9d1cd}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#111614;--card:#1a211e;--ink:#e6ece9;--muted:#9fb0a8;--line:#2d3833;--accent:#4cc3a3;--soft:#1f3a32;--miss:#3a4641}}}}
:root[data-theme="dark"]{{--bg:#111614;--card:#1a211e;--ink:#e6ece9;--muted:#9fb0a8;--line:#2d3833;--accent:#4cc3a3;--soft:#1f3a32;--miss:#3a4641}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}}
.wrap{{max-width:980px;margin:0 auto;padding:32px 16px 64px}}h1{{font-size:30px;margin:0 0 6px}}h2{{font-size:20px;margin:36px 0 12px}}h3{{font-size:15px;margin:0 0 10px}}a{{color:var(--accent)}}
.muted{{color:var(--muted)}}.lede{{color:var(--muted);max-width:68ch}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:24px 0}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}}.kpi b{{display:block;font-size:30px;line-height:1.1}}.kpi span{{color:var(--muted);font-size:14px}}
.panel{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}}
.bar{{display:grid;grid-template-columns:minmax(0,220px) 1fr auto;gap:12px;align-items:center;margin:8px 0}}.bl{{font-size:14px}}
.bt{{height:14px;background:var(--soft);border-radius:7px;overflow:hidden}}.bf{{height:100%;background:var(--accent)}}.bv{{font-variant-numeric:tabular-nums;font-weight:700;font-size:14px;white-space:nowrap}}
@media (max-width:600px){{.bar{{grid-template-columns:1fr auto}}.bt{{grid-column:1/-1;order:3}}}}
.tablewrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
td.hit,td.miss{{text-align:center;font-size:16px}}td.hit{{color:var(--accent)}}td.miss{{color:var(--miss)}}td.k{{color:var(--muted);font-size:12px}}tr.benign td.t{{color:var(--muted)}}
.sr{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}
.ev{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin:12px 0}}.pair{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}}
figure{{margin:0}}figure img{{width:100%;height:auto;border:1px solid var(--line);border-radius:8px;display:block;background:#fff}}figcaption{{font-size:13px;color:var(--muted);margin-top:4px}}
ul.notes li{{margin:6px 0}}code{{font-size:13px}}
</style></head><body><div class="wrap">
<h1>LinguaCheck results</h1>
<p class="muted" style="font-size:14px;margin:0 0 12px"><a href="../">About</a> · <a href="../app/">Try the demo</a> · <a href="https://github.com/Jeff-rey13/linguacheck">Source code</a></p>
<p class="lede">Multilingual UI regression testing on a demo recreation-centre booking flow. {nd} realistic UI defects and {nb} harmless restyles were seeded one at a time,
then each strategy was run at {", ".join(str(w) for w in S["viewports"])}px phone widths. Generated {e(S["generated"])} from {S["runs"]} page loads in {S["seconds"]}s.</p>

<div class="kpis">
<div class="kpi"><b>{eng["caught_n"]}/{nd}</b><span>defects caught by English-only testing</span></div>
<div class="kpi"><b>{pse["caught_n"]}/{nd}</b><span>caught with pseudo-localisation added</span></div>
<div class="kpi"><b>{real["caught_n"]}/{nd}</b><span>caught with Chinese, Bengali, Tamil and Thai added</span></div>
<div class="kpi"><b>{max(eng["false_alarm_n"], pse["false_alarm_n"], real["false_alarm_n"])}/{nb}</b><span>false alarms on harmless changes, any strategy</span></div>
</div>

<h2>Defects caught by each strategy</h2>
<div class="panel">{strategy_bars}</div>

<h2>What I expected, and what happened</h2>
<div class="panel"><ul class="notes">
<li><b>English-only testing missed {nd - eng["caught_n"]} of {nd} defects.</b> {len(eng_missed)} of them were layout bugs that only show up once text is longer than English, and other strategies caught them. The last one was missed by everything (see Limitations).</li>
<li><b>My hypothesis was that real scripts would catch bugs nothing else could. On this test set they didn't.</b> No defect was caught only by a real language. Pseudo-localisation, the cheap industry shortcut, caught {pse["caught_n"]} with {pse["page_loads_per_release"]} page loads per release, against {real["caught_n"]} for real languages with {real["page_loads_per_release"]}.</li>
<li><b>Tamil did almost all of the real-language work</b> ({S["per_language_catches"]["ta"]}/{nd} on its own), because its words are much longer than the English source. Chinese and Thai, which are often shorter, caught fewer defects than English.</li>
<li><b>Practical recommendation:</b> run English and pseudo-localisation on every build, since that pair caught every defect any strategy caught. Keep Tamil as one real-script check, because pseudo-localisation only stretches Latin text and cannot reproduce script-specific problems that this test set did not include.</li>
</ul></div>

<h2>Catches by single language</h2>
<div class="panel">{lang_bars}</div>

<h2>Evidence: defects English-only testing passed</h2>
<p class="muted">Same seeded defect, same 360px screen. Left: English, which the checks pass. Right: the language that exposed it.</p>
{"".join(gallery)}

<h2>Every seeded change</h2>
<div class="panel tablewrap"><table>
<thead><tr><th scope="col">ID</th><th scope="col">Change</th>{"".join(f'<th scope="col">{e(LANG_NAMES[l])}</th>' for l in S["languages"])}<th scope="col">Checks that fired</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>

<h2>Limitations</h2>
<div class="panel"><ul class="notes">
<li><b>I wrote both the defects and the checks.</b> The defects follow common real-world CSS regressions and were fixed before the first run, but results on a real app's history of bugs could differ.</li>
{v1_line}
<li><b>D08 was missed by every strategy.</b> The summary rows stopped wrapping, but none of the translated values were long enough to overflow, so there was no visible symptom to catch. It is a latent bug, not a detected one.</li>
<li><b>Translations are machine-generated and unreviewed.</b> String length and glyph height are realistic, but the wording is placeholder text.</li>
<li><b>Some problems are invisible to these checks.</b> In the clean Tamil build, a long bottom-tab label breaks in the middle of a word. Nothing overflows, so no check fires, but a native reader would notice. Catching that needs a line-break check or a human review.</li>
<li><b>One demo page, Chromium only, three phone widths.</b> No real devices, no iOS Safari, no user data. The demo is not affiliated with any agency.</li>
<li>Clean-baseline findings: {sum(S["clean_baseline_findings"].values())} across all languages and widths, so every flagged item above is caused by the seeded change.</li>
</ul></div>
</div></body></html>"""

out = ROOT / "report" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(page, encoding="utf-8")
print(out, round(out.stat().st_size / 1024), "KB")
