# WO-CO-100 · v1 · Verification report

**WO-CO-100 · v1 delivery · Controlling brief: V3 (09f7655aaf5ddbb8a411116718e0ce909e24bd6e) · Baseline: reconstruction; Pre-Order not compared (I-1 open)**

Author: JARVIS (Claude). Run: `python3 -I deliveries/WO-CO-100/v1/tests/verify.py` from the repo root, at 2026-11-20T11:01:44Z. Raw results: `test-output.json`. These are the actual results of that run, not expectations.

## Result: PARTIAL — 22 PASS · 0 FAIL · 2 INFO · 1 NOT RUN · 4 BLOCKED

| ID | Check | Result | Detail |
|---|---|---|---|
| AC7-1..4 | 30 EN posts · 30 AR posts · 12 video scripts (6 EN, 6 AR) · 10 briefs | PASS | Counted from item headings |
| AC7-5/6 | 30-day calendar D1–D30; all 60 posts scheduled exactly once, incl. EN-21 (D26) and EN-24 (D25) | PASS | EN-26 reruns are counted as second-slot reruns, not new items |
| AC7-7/8 | 90-day roadmap (Phase 0 + three 30-day phases); three budgets, no zero-spend | PASS | |
| AC2-1/2 | Every cost cell tagged; no [QUOTED] claimed | PASS | 42 cost cells, all [ESTIMATE]. No vendor was contacted (G-12) |
| SRC-1 | Every cited Sxx is defined in SOURCES.md | PASS | 33 cited, 38 defined |
| SRC-2 | Items with no source | INFO | 9 items: EN-01, EN-26, EN-30, AR-01, AR-18, AR-20, AR-21, AR-30, V-AR-01. JARVIS reviewed each: these are welcome/standards/house posts, wrap templates or explainers with no factual claim; V-AR-01's unsourced legal line was removed |
| AC5-1 | No CTA, odds, tips, bonus codes, registration wording or inducement (G-11 AC5, G-04 red lines) | PASS | 5 pattern hits, all inside "we don't publish tips/odds" negations. Note: «مراهنات» appears in AR-09/AR-10 as enforcement news (illegal betting cases), which is reporting, not wordplay |
| AC5-2 | No operator or registration links in items | PASS | 0 URLs in item bodies; links live only in SOURCES.md |
| AC3-1 | D-2 items tagged [LEGAL-CHECK] (EN-11, AR-02, AR-10, AR-11, V-EN-06, V-AR-03, B10) | PASS | |
| AC3-2 | Legal vocabulary without [LEGAL-CHECK] (heuristic) | INFO | 17 items flagged on the first run. JARVIS read each one: EN-20 and AR-26 (a vendor-licensing claim on a secondary source) were **tagged during verification**. The remaining 15 are people, dates or corporate news, a HYPOTHESIS-marked item (AR-17), or neutral notes, and none states the law of a GCC state |
| AC6-1 | EN/AR story overlap below 30% every week (G-13, no exception) | PASS | W1 27.3% · W2 16.7% · W3 0% · W4 16.7% · W5 0%. W1 is close to the limit |
| AC6-2/3 | Calendar story keys match topic-tags.json; all keys defined in TAXONOMY.md | PASS | 60/60 |
| AC8-1 | Numeric Day 30/60/90 target for every KPI in every scenario | PASS | 12 KPI rows × 3 scenarios |
| GOV-1..3 | Operations design is design-only; G-12 gate; G-06/G-02 open; seven red lines in the checklist; V3 header in every file | PASS | |
| AR-1 | Arabic posts are written in Arabic | PASS | 94% Arabic letters (the Latin letters are names, brand and source IDs) |
| EXT-1 | Source URLs reachable and archived (D-10) | NOT RUN | Archive plan is in OPERATIONS-DESIGN §8. Reviewer D's spot check found 26 of 39 URLs returning 200 |
| EXT-2 | Platform analytics capabilities | BLOCKED | ASSUMPTION until checked against official platform docs (MB-06); no accounts exist (G-12) |
| EXT-3 | Pre-Order point-by-point comparison | BLOCKED | Original not in the repository (I-1, KITT) |
| EXT-4 | Legal review of [LEGAL-CHECK] items | BLOCKED | Opinion authorized (G-03) but not yet obtained |
| EXT-5 | Native Arabic editor review | BLOCKED | Editor not appointed (G-05) |

## Limitations (stated plainly)

- All costs are **JARVIS estimates**, not quotes. KPI targets are **planning targets, not forecasts or guarantees**; no baseline exists.
- The automated checks are text scans: they prove the counts, tags, links and overlap arithmetic, **not** editorial quality or legal correctness.
- Nothing is published, created, bought or deployed. Deployment and rollback: N/A.
- The [VERIFY] items are still open: the Sharjah government Fri–Sun weekend, and the Telegram Ads gambling ban (weak source S30). Also open: the S14 date (EN-21 gate) and the S24 EWC-location conflict.
- Open for G: **G-01** (which budget runs the first 90 days; the budgets are now ready for that choice), **G-02** (Arabic brand form), **G-06** (owning entity and jurisdiction), and **G-12** (each account action).
