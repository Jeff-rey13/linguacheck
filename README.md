# LinguaCheck

**Multilingual UI regression testing for mobile eServices.**
Find the layout bugs that English-only testing misses, before they reach the
users who depend on their own language.

[![LinguaCheck tests](https://github.com/Jeff-rey13/linguacheck/actions/workflows/linguacheck.yml/badge.svg)](https://github.com/Jeff-rey13/linguacheck/actions/workflows/linguacheck.yml)

| | |
|---|---|
| **Live site** | https://jeff-rey13.github.io/linguacheck/ |
| **Interactive demo** | https://jeff-rey13.github.io/linguacheck/app/ |
| **Full results** | https://jeff-rey13.github.io/linguacheck/report/ |

---

## Why I built this

Government apps for migrant workers in Singapore are deliberately
multilingual. MOM's FWMOMCare app, for example, is offered in several
languages so that workers who are not proficient in English can still request
help, report unsafe workplaces, see a doctor and book recreation-centre
facilities ([MOM](https://www.mom.gov.sg/eservices/fwmomcare)). By February 2022 it had
been downloaded more than a million times
([NCS case study](https://www.ncs.co/en-sg/knowledge-centre/tracking-the-health-status-of-migrant-workers-in-a-pandemic)).

The gap I noticed is in how apps like this are usually tested. Automated UI
regression tests are typically written and run in English. But the same screen
behaves differently in another language:

- Tamil and Bengali labels are often much **longer** than the English source,
  so fixed-width buttons, tabs and badges clip or overflow.
- Thai has **no spaces between words**, so text breaks in unexpected places.
- Different scripts have **taller glyphs**, so text inside fixed-height boxes
  gets cut off at the top or bottom.

So a release can pass every test in English and still ship a "Confirm booking"
button that is unreadable in Tamil. **The people most likely to hit the bug are
the people the multilingual design was built for, and English-only testing
gives them the least protection.**

LinguaCheck turns that observation into a question that can be measured:

> How many layout bugs does English-only testing miss, and what is the cheapest
> way to catch them?

## What it does

LinguaCheck is a small, working version of a multilingual regression-testing
pipeline:

1. **A demo eService.** A recreation-centre facility booking flow (my own
   design, clearly labelled as a demo) in English, Chinese, Bengali, Tamil and
   Thai, plus a *pseudo-locale* that stretches English text by about 40% with
   accented letters, a common industry shortcut.
2. **Automated checks.** A Playwright harness loads every screen in every
   language at three phone widths (320, 360 and 412px) and runs checks for:
   clipped text, text running off-screen, sideways page scrolling, overlapping
   text and buttons, content hidden behind fixed bars, missing accessible
   names, touch targets that are too small, tiny text and low colour contrast.
3. **A fair experiment.** 24 realistic UI defects (fixed widths, `nowrap`,
   fixed heights, removed labels and so on) and 8 harmless restyles are applied
   one at a time. Each run is compared with a clean baseline in the same
   language and width, so every finding is caused by the change being tested.
4. **A results report** comparing three testing strategies, with
   side-by-side screenshots of each defect passing in English and failing in
   another language.
5. **Continuous integration.** GitHub Actions reruns the whole experiment on
   every push, so the numbers are reproducible rather than hand-typed.

```
 seeded change ──► demo app ──► 6 languages × 3 phone widths ──► checks
                                                                    │
       clean baseline (same language + width) ──────── diff ◄───────┘
                                                          │
                                       new findings = caused by the change
                                                          │
                          score each strategy: caught? false alarm? cost?
```

## Results

594 page loads in about 110 seconds. GitHub Actions reruns the same experiment on every push.

| Strategy | Defects caught | False alarms on harmless changes | Page loads per release |
|---|---|---|---|
| English only | **15 / 24** | 0 / 8 | 3 |
| English + pseudo-localisation | **23 / 24** | 0 / 8 | 6 |
| English + Chinese, Bengali, Tamil, Thai | **22 / 24** | 0 / 8 | 15 |

The clean app produced **0 findings** in all 18 language and width
combinations, so nothing above is noise from the baseline.

**What the results show**

- **English-only testing missed 9 of 24 defects (38%).** Eight of them were
  layout bugs that only appear when text is longer than English, and other
  strategies caught them.
- **My original hypothesis was wrong, and that is a useful result.** I expected
  real scripts to catch bugs nothing else could. On this test set, no defect
  was caught *only* by a real language. Pseudo-localisation caught one more
  defect with less than half the page loads.
- **Not all languages are equally useful as tests.** Tamil alone caught 22 of
  24. Chinese and Thai each caught 12, fewer than English, because their
  strings are often shorter. Testing "more languages" is not automatically
  better; testing the *longest* ones is.
- **Practical recommendation:** run English and pseudo-localisation on every
  build, and keep Tamil as one real-script check for problems that stretching
  Latin text cannot reproduce (script height, line breaking).

Screenshots and the per-defect table are in the
[results report](https://jeff-rey13.github.io/linguacheck/report/).

## Impact

**For the people using the app.** Fewer broken screens in their own language:
buttons they can read, booking steps they can finish, health advisories that
are not cut off. A clipped button in English is an annoyance; in a worker's
only readable language it can mean a task they cannot complete without help.

**For the team building the app.**

- **Catches a class of bugs the current process structurally misses**, before
  release rather than through user complaints.
- **Turns "we support six languages" into something measured.** Coverage per
  language becomes a number that can be tracked release to release.
- **Spends test time where it pays off.** The experiment shows that the
  cheapest strategy (English + pseudo-localisation) caught the most defects,
  so a team can get most of the protection at a fraction of the cost of
  testing every language on every build.
- **Gives developers evidence, not just a red cross.** Each finding names the
  element, the check that fired, the language and the screen width, with a
  screenshot.

## What it could produce at a larger scale

This repo tests one demo flow. Developed further and run against a real app's
screens and bug history, the same approach could produce the following. These
are directions to test, not results I have measured.

| At scale it could… | What that would tell a team |
|---|---|
| Run every key user flow in every supported language on every build, as a CI gate | Whether a release breaks any language *before* it ships |
| Track findings per language and per screen over many releases | Which screens and which languages break most often, so design fixes go where they matter |
| Replay the app's **real past bugs** instead of seeded ones | Whether pseudo-localisation still matches real-language testing on real defects, which is the key open question from this experiment |
| Weight languages by how many users actually use each one | A test plan that protects the most users per minute of test time |
| Add real devices and WebKit (iOS Safari) | Whether bugs depend on the phone and browser, not only the language |
| Generate test flows with a large language model and score them against the same seeded defects | Whether AI-written tests find as many bugs as hand-written ones, measured rather than assumed |
| Add a line-break quality check for Tamil and Thai | Problems that no current check can see (see Limitations) |

**Rough cost.** The demo ran at about 0.2 seconds per page load. As an
illustration only: 20 flows × 6 languages × 3 widths = 360 page loads, which
would take a little over a minute at that speed. Real apps load more slowly,
so actual times would be higher, but the approach is cheap enough to run on
every build.

## Try it yourself

**In the browser:** open the [demo](https://jeff-rey13.github.io/linguacheck/app/),
pick a **seeded change** from the dropdown (for example *D03* or *D15*), then
switch the app language between English, Tamil and Pseudo. Bugs that look fine
in English break in the other languages.

**Run the full experiment locally:**

```bash
pip install -r requirements.txt
python -m playwright install chromium
python harness/run.py      # about 2 minutes, 594 page loads
python harness/report.py   # writes report/index.html
```

## How it works

1. Load the clean app for each language and width and record every finding.
2. Load the app with one seeded change applied and run the same checks.
3. Any finding not in the clean baseline for the same language and width is
   caused by the change. A defect counts as **caught** by a strategy if any of
   that strategy's languages flags it at any width. A harmless change that gets
   flagged is a **false alarm**.

## Repository layout

```
index.html      Landing page
app/            Demo booking flow (vanilla HTML/CSS/JS, self-hosted Noto fonts)
  app.js        App logic (safe DOM building, allowlisted URL parameters)
  i18n.js       Strings in English, Chinese, Bengali, Tamil, Thai + pseudo-locale
  bugs.js       24 seeded defects and 8 harmless changes
harness/
  checks.js     In-page layout and accessibility checks
  run.py        Runs every language × width × change, diffs against baseline,
                scores each strategy, saves evidence screenshots
  report.py     Builds the self-contained results page
results/        summary.json, raw.json, summary_v1.json, screenshots
report/         Results page
.github/        CI workflow that reruns the experiment on every push
```

## Security

The live site is static (GitHub Pages, HTTPS only) with no backend, no
database, no cookies, no third-party scripts and no form that submits anywhere.

- Every page sets a Content Security Policy that only allows the site's own
  files, blocks outside connections and disables form submission. The landing
  page and results page run no scripts at all.
- The demo inserts all text with `textContent`, never as HTML, and checks the
  `lang` and `bug` URL parameters against fixed allowlists. I tested it with
  script-injection and prototype-key payloads (`<script>`, `onerror=`,
  `__proto__`, `constructor`): none executed, and the page fell back to
  defaults.
- No secrets are stored in the repo. The CI workflow has read-only permissions
  and does not keep its checkout token.
- GitHub Pages cannot set custom HTTP headers, so header-only protections such
  as `frame-ancestors` are not available. With no logins or actions on the
  site, the risk from that is low.

## Limitations

I have tried to be clear about what this experiment does and does not show.

- **I wrote both the defects and the checks.** The defects follow common CSS
  regressions and were fixed before the first run, but a real app's bug history
  could give different numbers.
- **The checker had a bug of its own.** Version 1 ignored overlaps inside fixed
  bars and missed defect D15. I fixed it after seeing the miss, so the version 2
  numbers above are slightly optimistic. Version 1 scored 15, 22 and 21 of 24
  (`results/summary_v1.json`).
- **D08 was missed by every strategy.** The summary rows stopped wrapping, but
  no value was long enough to overflow, so there was no visible symptom.
- **Some problems are invisible to these checks.** In the clean Tamil build, a
  long tab label breaks mid-word. Nothing overflows, so no check fires.
- **Translations are machine-generated** and have not been reviewed by native
  speakers. String length and glyph height are realistic; the wording is not.
- **One demo flow, Chromium only, three phone widths.** No real devices, no
  iOS Safari and no real user data.
- **Not affiliated with any government agency.** The demo uses its own design
  and collects nothing.

## Author

Noel Jeffrey Narala Thomas, Year 2 Computer Engineering, Nanyang Technological
University. [GitHub](https://github.com/Jeff-rey13) ·
[LinkedIn](https://linkedin.com/in/noeljeffreythomas)
