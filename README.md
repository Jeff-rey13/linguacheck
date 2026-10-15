# LinguaCheck

Multilingual UI regression testing for mobile eServices.

**Live site:** https://jeff-rey13.github.io/linguacheck/ ·
**Demo:** https://jeff-rey13.github.io/linguacheck/app/ ·
**Results:** https://jeff-rey13.github.io/linguacheck/report/

Apps for migrant workers in Singapore are offered in several languages so that
workers who are not proficient in English can use them. UI regression tests,
however, are usually run in English only. A button that fits "Confirm booking"
can clip "முன்பதிவை உறுதிசெய்". LinguaCheck asks a simple question: **how many
layout bugs does English-only testing miss, and what is the cheapest way to
catch them?**

## Results (run on 15 Oct 2026)

24 realistic UI defects and 8 harmless restyles were seeded one at a time into
a demo booking flow, then tested in 6 language settings at 320, 360 and 412px
phone widths (594 page loads, about 110 seconds).

| Strategy | Defects caught | False alarms | Page loads per release |
|---|---|---|---|
| English only | 15 / 24 | 0 / 8 | 3 |
| English + pseudo-localisation | 23 / 24 | 0 / 8 | 6 |
| English + Chinese, Bengali, Tamil, Thai | 22 / 24 | 0 / 8 | 15 |

What I found:

- English-only testing missed 9 of 24 defects. 8 were layout bugs that only
  show up with longer text; the 9th was missed by every strategy.
- **My hypothesis was wrong on this test set.** I expected real scripts to
  catch bugs nothing else could. No defect was caught only by a real language.
  Pseudo-localisation caught more, with fewer page loads.
- Tamil alone caught 22 of 24. Chinese and Thai each caught 12, fewer than
  English, because their strings are often shorter.
- Recommendation: run English + pseudo-localisation on every build, and keep
  Tamil as one real-script check for problems pseudo-localisation cannot
  reproduce.

Full results with screenshots: `report/index.html`.

## What's in the repo

```
app/            Demo booking flow (vanilla HTML/CSS/JS, self-hosted Noto fonts)
  i18n.js       Strings in English, Chinese, Bengali, Tamil, Thai + pseudo-locale
  bugs.js       24 seeded defects and 8 benign changes (load with ?bug=D01)
harness/
  checks.js     In-page checks: clipped text, off-screen text, page side-scroll,
                overlaps, content hidden behind fixed bars, missing accessible
                names, small touch targets, tiny text, low contrast
  run.py        Runs every language x width x seeded change, diffs against the
                clean baseline, scores each strategy, saves evidence screenshots
  report.py     Builds the self-contained results page
results/        summary.json, raw.json, summary_v1.json, screenshots
report/         index.html
```

## How it works

1. Load the clean app for each language and width and record every finding.
   The clean baseline has **0 findings** in all 18 combinations.
2. Load the app with one seeded change applied and run the same checks.
3. Any finding not in the clean baseline for the same language and width is
   caused by the change. A defect counts as caught by a strategy if any of that
   strategy's languages flags it at any width. A benign change that gets flagged
   is a false alarm.

## Run it

```bash
pip install -r requirements.txt
python -m playwright install chromium
python harness/run.py      # about 2 minutes
python harness/report.py   # writes report/index.html
```

Try the demo by opening `app/index.html?lang=ta` or `app/index.html?lang=ta&bug=D03`
through any static server (for example `python -m http.server -d app`).

GitHub Actions (`.github/workflows/linguacheck.yml`) runs the full evaluation on
every push and uploads the report.

## Security

The live site is static (GitHub Pages, HTTPS only) with no backend, no
database, no forms that submit anywhere, no cookies and no third-party scripts.

- Every page sets a Content Security Policy that only allows the site's own
  scripts, fonts and styles, blocks all outside connections and disables form
  submission. The results and landing pages allow no scripts at all.
- The demo inserts all text with `textContent`, never as HTML, and checks the
  `lang` and `bug` URL parameters against fixed allowlists. Tested with
  script-injection and prototype-key payloads (`<script>`, `onerror=`,
  `__proto__`, `constructor`): none executed, and the page fell back to defaults.
- No secrets are stored in the repo. The CI workflow runs with read-only
  permissions and does not keep the checkout token.
- GitHub Pages cannot set custom HTTP headers, so protections that only work as
  headers (such as `frame-ancestors`) are not available. With no logins or
  actions to trick a user into, the risk from framing is low.

## Limitations

- **I wrote both the defects and the checks.** The defects follow common CSS
  regressions (fixed widths, nowrap, fixed heights, removed labels) and were
  fixed before the first run, but a real app's bug history could give
  different numbers.
- **The checker had its own bug.** Version 1 ignored overlaps inside fixed bars
  and missed D15. I fixed it after seeing the miss, so version 2 numbers are
  slightly optimistic. Version 1 scored 15, 22 and 21 of 24
  (`results/summary_v1.json`).
- **D08 was missed by everything.** The rows stopped wrapping, but no value was
  long enough to overflow, so there was nothing visible to catch.
- **Some problems are invisible to these checks.** In the clean Tamil build a
  long tab label breaks mid-word. Nothing overflows, so no check fires.
- **Translations are machine-generated and unreviewed** by native speakers.
- One demo page, Chromium only, no real devices. The demo is not affiliated
  with any government agency and uses no real user data.

## Next steps

- LLM-generated test flows, measured against the same seeded defects.
- Line-break quality check for scripts like Tamil and Thai.
- Run against real device widths and WebKit.
