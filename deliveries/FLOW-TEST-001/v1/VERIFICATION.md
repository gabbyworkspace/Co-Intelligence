# FLOW-TEST-001 · v1 · Verification (Step 9)

Built and verified by JARVIS (scheduled run, manual pickup; the coint/ automation is NOT deployed).
Controlling brief: `FLOW-TEST-001/INITIAL-BRIEF-v1.2.md` @ `4b6fbe4367e3412c286badde5a94564bdffd2bc4`.
Governing package: `council/FLOW-TEST-001/MANIFEST-c1-02.json` (FLOW-TEST-001-C1-COUNCIL-02) @ `01d5f11c42684a604924817bdef5da55ed897b38`.
Delivery commit: the commit that adds this file (cited on issue #2).

## Deliverable

| File | SHA-256 |
|---|---|
| `index.html` | `d3945294a39c602bd22424e34e131bfacba5d322fef34f74f3f0ae07cb25392b` |
| `test_index.js` | `0752571d7395adc01cb145392861ce046406f150a31c5dda2ffc13ece7ac25e1` |

`index.html` is one standalone file with no dependencies. On load it shows `Co-Intelligence workflow test passed.` and one button `Complete handoffs`. The first click sets the message to `All agents completed their handoffs.` with `textContent`; later clicks return early and change nothing (G-06). CSP meta: `default-src 'none'`, with the inline script and style allowed only by their SHA-256 hashes; `base-uri 'none'`, `form-action 'none'`. No external resources, network calls, simulated agents or deployment (rollback N/A).

## Automated test (C11)

Command: `node test_index.js` (Playwright, pre-installed headless Chromium 153.0.8010.12, file:// URL, no network).
Run: 2026-11-14T17:28:42.679Z UTC · exit code 0 · **14/14 PASS**. Raw output: `test-output.json`.

| ID | Check | Result |
|---|---|---|
| S1 | No external URLs in source | PASS |
| S2 | No `src=`/`href=` attributes | PASS |
| S3 | Restrictive CSP meta (`default-src 'none'`) | PASS |
| S4 | Text updated via `textContent` only (no innerHTML/document.write/eval) | PASS |
| S5 | No fetch/XHR/WebSocket/sendBeacon/dynamic import | PASS |
| R1 | Initial text exactly `Co-Intelligence workflow test passed.` | PASS |
| R2 | Button label exactly `Complete handoffs` | PASS |
| R3 | Exactly one button | PASS |
| R4 | No quotation marks displayed (initial) | PASS |
| R5 | First click shows exactly `All agents completed their handoffs.` | PASS |
| R6 | Three more clicks: text and DOM unchanged | PASS |
| R7 | No quotation marks displayed (final) | PASS |
| R8 | Only request made is the file itself | PASS |
| R9 | No console errors or CSP violations | PASS |

Negative control (not committed): with the `done=true;` statement removed from a scratch copy, the test FAILED R5/R6 (the edited script no longer matches the CSP hash, so the browser blocked it). This shows the test detects a broken or tampered script and that the CSP is enforced.

## Limitations and unresolved issues

- Tested in Chromium only (no Firefox/WebKit run). Behaviour uses only standard DOM APIs.
- C17–C19 (automated pickup, duplicate replay, 5-minute recovery) stay **BLOCKED**: the automation engine (PR #1) is not deployed. Per G-02 the overall test result can be at best **PARTIAL**.
- C12 (KITT delivery review), C13 (founder presentation and review email) and C14 (G's final approval) are not done yet.
- The tag `FLOW-TEST-001-c1-council-frozen` was created locally but the push was refused by this environment's git connection (remote hung up). It is not on GitHub; the freeze is evidenced by commit `01d5f11c42684a604924817bdef5da55ed897b38`. The delivery tag `FLOW-TEST-001-v1` is created only after KITT's review (Step 10).
- WORKFLOW amendments C-3/A-5/C-4 are prepared in `FLOW-TEST-001/WORKFLOW-AMENDMENTS-c1.md` but not applied to the root `WORKFLOW.md` (outside the unattended run's write scope).
