# FLOW-TEST-002 — JARVIS Step 3 review of the approved initial brief (Cycle 1)

- Reviewer: JARVIS (scheduled run, manual pickup — the coint/ automation server is not deployed)
- Reviewed: `FLOW-TEST-002/INITIAL-BRIEF-v1.0.md` @ `21210b21afc4172612272cd68956372173dc4096`, which incorporates `FLOW-TEST-002/INITIAL-BRIEF-v0.1.md` @ `5f15b66fadd644a4e49a1eeaa8bac689f61851f5` by reference
- Input: KITT handoff, issue #4 comment 6881736253 (2026-11-14T17:50:49Z)
- Governing docs read on main @ 21210b2: `WORKFLOW.md` v2.0, `config/routing.yaml`, `docs/FOUNDER_DECISION_VALIDATION.md`
- Review time: 2026-11-14T18:10Z
- Scope: completeness, consistency, feasibility, dependencies, acceptance criteria (WORKFLOW Step 3). This review does not change scope and is not a Council review.

## Verdict

**Feasible; RETURNED TO KITT for Step 4 revision.** The deliverable is small and buildable within the stated restrictions (one static HTML file, testable with Node + Playwright/Chromium in JARVIS's environment). The findings below are mostly testability gaps in the acceptance checks plus three consistency/dependency points. Two items (J-01, J-08) need input that only G can give; KITT should record G's words rather than JARVIS inferring them.

## Findings

| ID | Severity | Area | Finding | Requested action (KITT, Step 4) |
|---|---|---|---|---|
| J-01 | High | Consistency | Step 11 recipients conflict. v0.1/v1.0 and issue #4 say the review package goes to baileys.resystem@gmail.com **and** g@resystem.org "per G's latest additional-recipient instruction". `WORKFLOW.md` v2.0 Step 11.3, the AWAITING_FOUNDER_DECISION row and JARVIS's standing instructions say **baileys.resystem@gmail.com only** (g@resystem.org receives only the post-closure report). No verbatim G words, date or channel are cited for the additional recipient. | Record G's exact instruction (words, date, channel) in the brief, or drop it. Until a recorded G instruction exists, JARVIS will send the Step 11 package to Baileys only and will not email g@resystem.org before closure. |
| J-02 | Medium | Completeness | The controlling brief is split: v1.0 is a summary that incorporates v0.1, and v0.1 still carries "Status: PROPOSED / AWAITING FOUNDER…". Freezing a Council package on that pair is ambiguous. | Publish one self-contained controlling brief (e.g. `INITIAL-BRIEF-v1.1.md`) containing the full requirements and acceptance checks, with G's approval record, and marking v0.1 as superseded history. No scope change. |
| J-03 | Medium | Acceptance | Counter wording is defined only for `0 of 3 complete`. | State the exact string for every state: `0 of 3 complete`, `1 of 3 complete`, `2 of 3 complete`, `3 of 3 complete`; and whether the counter stays visible next to `All sample tasks complete.` (JARVIS proposal: yes, both visible at 3/3). |
| J-04 | Medium | Acceptance / security | "Restrictive CSP" is not testable as written. | Name the required policy, delivered as a `<meta http-equiv="Content-Security-Policy">` (a file:// page has no headers). JARVIS proposal: `default-src 'none'; script-src 'sha256-<hash of the inline script>'; style-src 'sha256-<hash>' (or 'unsafe-inline' for styles only); img-src 'none'; connect-src 'none'; form-action 'none'; base-uri 'none'`. No `'unsafe-inline'`/`'unsafe-eval'` for scripts. Note: `frame-ancestors` cannot be set via meta and is out of scope. |
| J-05 | Medium | Acceptance / a11y | "Keyboard operation works" has no pass condition; screen-reader announcement of the counter/message is unspecified. | Specify: each checkbox is reachable by Tab in label order, toggles with Space, has a visible focus indicator, and its `<label for>` (or wrapping label) gives the accessible name equal to the task text; counter and completion message are in an `aria-live="polite"` region. |
| J-06 | Low | Acceptance | Test environment and method for "no network calls / no console errors" are not stated. | Specify: loaded from `file://` in headless Chromium via Playwright; pass = zero requests other than the document itself, zero console errors/warnings, zero CSP violation reports. Other browsers: not tested (state as a limitation). |
| J-07 | Low | Completeness | Reload behaviour is implicit. "No storage" means state resets to `0 of 3 complete` on reload. | State this explicitly as expected behaviour. |
| J-08 | High | Dependency (needs G) | Closure path. C17–C19 must stay BLOCKED (engine not deployed) and FLOW-TEST-001's partial-closure exception is not inherited. As written, FLOW-TEST-002 can therefore never reach full PASS closure; it will stop at the Step 11/12 gate unless G explicitly authorises partial closure for this project. | Add to the brief: "Closure requires either the real engine evidence for C17–C19 or a separate explicit G decision authorising PARTIAL closure of FLOW-TEST-002." Raise it with G now (KITT channel) or at Step 11 — not inferred by JARVIS. |
| J-09 | Low | Dependency | WORKFLOW Step 10.4 requires tag `<ID>-v<N>`. Tags cannot be pushed from JARVIS's environment (seen in FLOW-TEST-001, K2). | Accept the delivery identified by full commit SHA with "tag pending (owner action)", and name who pushes the tag (repo owner). |
| J-10 | Low | Consistency | v0.1 Step 11 says JARVIS "presents the exact final version in authorized JARVIS chat". Scheduled JARVIS runs cannot reach the JARVIS chat; they can only email the review package and accept validated email replies. | Note in the brief that Step 11 may run by review email + validated reply (docs/FOUNDER_DECISION_VALIDATION.md) when no live JARVIS chat session happens. |
| J-11 | Low | Completeness | Evidence locations not named. | Name them: build + evidence in `deliveries/FLOW-TEST-002/v1/` (`index.html`, `VERIFICATION.md`, `test-output.json`); test table in `FLOW-TEST-002/TEST-RESULTS-c1.md`; Council return as a GRONK PR adding `council/FLOW-TEST-002/cycle-1/…` (do not merge). |
| J-12 | Info | Step 1 | KITT's Step 1 initial review email to Baileys is not sent/verified (KITT's own note). | KITT: send via an authorized KITT integration and record the Gmail ID as "ACCEPTED BY GMAIL (delivery unconfirmed)", or mark the substep BLOCKED in `FLOW-TEST-002/TEST-RESULTS-c1.md`. JARVIS will not send it (not JARVIS's step). Not a blocker for Steps 3–5. |

## Checked and fine

- Scope, sample deliverable, labels, title (`Sample Project Checklist`, in v0.1), initial state and completion/un-completion behaviour are clear and internally consistent.
- Restrictions (no external resources, analytics, storage, network, simulated agents/approvals) are clear and testable once J-04/J-06 are specified.
- G's Step 1 approval ("yes" to KITT's exact question, KITT chat) is recorded verbatim by KITT and scoped to the initial brief only — consistent with WORKFLOW Step 1 (G ↔ KITT channel).
- Feasibility: no external dependency; JARVIS environment has Node and Playwright + Chromium for the checks.

## Next

**Next owner: KITT (Step 4)** — publish the revised controlling brief addressing J-01…J-12 (or say per item why not), commit to main, and comment "→ JARVIS" on issue #4 with the new commit SHA. JARVIS then checks each item (Step 4) and freezes the Council package (Step 5).
