# FLOW-TEST-001 — Controlling brief v1.2 (Cycle 1)

**Authority:** G directly confirmed G-01, G-02, G-03 and G-06 in KITT chat; record `decisions/FLOW-TEST-001/c1-council-G-decisions.KITT_RECORD.md` @ `bdb9fcbce380c29928f2706f5ab2b734ffb78d26`. This is approval of the *controlling build brief*, **not** Step 11 final delivery approval. Based on GRONK's council proposal in PR #3 @ `4718d75fee4a6e7896a8ced7f8a8ff87fb024f99`, and JARVIS reconciliation `FLOW-TEST-001/RECONCILIATION-c1.md` and `FLOW-TEST-001/FINDING-DISPOSITIONS-c1.json` @ `dac970213ab748940ffb9ad63b1774dac9a9fd5c`.

## Build requirements

Deliver **one standalone dependency-free HTML file** at `deliveries/FLOW-TEST-001/v1/index.html`. On load show exactly `Co-Intelligence workflow test passed.`. Display a button labelled exactly `Complete handoffs`. On its first click, change the displayed text to exactly `All agents completed their handoffs.`. Subsequent clicks do nothing; the final message persists. Display no quotation marks. Preserve exact capitalization, spaces and punctuation. Use `textContent` for text updates, a restrictive CSP meta tag, and no external resources, network calls, simulated agents or dependencies. No deployment; rollback N/A. Handover: HTML file plus `VERIFICATION.md`.

## Scope, reviews and outcome

The 150-word limit applies **only to individual reviews**, not to briefs, annexes, findings indexes or other records (G-03). Each independent Council review must identify the frozen package SHA. Only version-pinned, real evidence counts. Do not claim an agent, email, automation, verification, founder approval or deployment succeeded without evidence.

Record each check C01–C19 with result, actor, owner, verifier, input/output SHA or URL, UTC time, and relevant email ID in `TEST-RESULTS.md`. Record unavailable checks as BLOCKED, never PASS. **G-02:** closure may proceed with C17–C19 BLOCKED if all other required closure conditions are satisfied, but the overall test outcome is **PARTIAL**, not PASS. No automated pickup, deduplication or recovery PASS is implied by that exception. C14 (final founder approval) and the independent delivery review remain mandatory.

Initial/final review email recipient: `baileys.resystem@gmail.com`. Only JARVIS sends the closure report to `g@resystem.org` after valid final founder approval and KITT's decision record. Gmail API acceptance is not proof of inbox delivery. No duplicate sends.

## Acceptance annex (C01–C19)

For every check, evidence must identify an actual artifact or run; timestamps and actor identity must not be invented.

| ID | Owner | Pass condition / required evidence |
|---|---|---|
| C01 | KITT/G | Initial v1.0 published; G's exact initial confirmation and initial email acceptance recorded with available evidence |
| C02 | JARVIS | Review of pinned v1.0 posted with findings and source link |
| C03 | KITT | v1.1 revision and response posted with commit and handoff link |
| C04 | JARVIS | Frozen manifest, pinned commit and actual freeze timestamp; re-freeze v1.2 after change |
| C05 | GRONK | Same frozen SHA dispatched to A–D; assignment evidence |
| C06 | Reviewer A | Independent review of frozen SHA, reviewer attribution and time |
| C07 | Reviewer B | Independent review of frozen SHA, reviewer attribution and time |
| C08 | Reviewer C | Independent review of frozen SHA, reviewer attribution and time |
| C09 | Reviewer D | Independent review of frozen SHA, reviewer attribution and time |
| C10 | GRONK | Council return includes all four reviews, proposed draft, index and conflict log at pinned PR commit |
| C11 | JARVIS | HTML exists; automated test verifies both exact strings, first-click behavior, repeat-click no-op and no external resources; record test output |
| C12 | KITT | JARVIS requests internal delivery review; KITT returns findings; JARVIS dispositions recorded |
| C13 | JARVIS | Exact final version presented to G in authorized JARVIS chat; review email sent via Gmail and logged with actual message ID, not claimed delivered |
| C14 | G/JARVIS/KITT | G explicitly approves exact final delivery version via authorized JARVIS gate; trusted validation and KITT GitHub record exist; otherwise BLOCKED |
| C15 | JARVIS automation | Closure preconditions met; closure record and tag created only after required approvals; G-02 exception documented |
| C16 | JARVIS | One final closure report email to `g@resystem.org`, deduplicated and logged |
| C17 | JARVIS automation | Real event picked up automatically, with service/run/event ID and UTC evidence; otherwise BLOCKED |
| C18 | JARVIS automation | Same event replay produces no duplicate action; event and skip logs; otherwise BLOCKED |
| C19 | JARVIS automation | Deliberate missed pickup recovered by actual five-minute scan without duplicate action; otherwise BLOCKED |

## Disposition and governance boundaries

Implement the accepted JARVIS-owned corrections in `FINDING-DISPOSITIONS-c1.json` at the cited reconciliation commit: expanded manifest with blob SHAs and governing files, evidence table, precise timestamps where available, initial email procedure, untrusted-input handling, mail deduplication, and automated HTML tests. JARVIS owns those workflow/configuration changes and must re-freeze the changed package. The PR #3 Council files remain unmodified and unmerged pending JARVIS's integration review.

G-01, G-02, G-03 and G-06 are resolved by the direct KITT-chat confirmation above. G-04, G-05, G-07–G-11 remain OPEN and must not be silently decided or implemented. No permission, privacy, signed-commit, branch-protection, or email-policy change is authorized here. Preserve v1.0, v1.1 and the original Council proposal.
