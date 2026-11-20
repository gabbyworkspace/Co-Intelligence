# WO-CO-100 (AcesBook GCC) · Cycle 1 · Council Findings Index

Package `WO-CO-100-C1-COUNCIL-01` · Freeze SHA `462d3da2fc2e4764a52d4c2eb99b7c500aeec644` (manifest blob `42e568b7`; content commit `3b776f4`)
Prepared by GRONK (Council Coordinator), 2026-11-20 09:55 UTC / 13:55 Dubai (UTC+4). Source texts: `review-A.md`, `review-B.md`, `review-C.md` and `review-D.md`, kept verbatim and unchanged.
All four reviews cite the freeze SHA and package ID, and all report that the 19 manifest blobs match. All four are complete. Each reviewer states it worked independently.

Counts: **A 9 · B 8 · C 12 · D 16 = 45 findings.**
Severity: A 3 High / 4 Medium / 2 Low · B 2 / 4 / 2 · C 2 High / 7 Medium / 2 Low / 1 Info · D 4 / 8 / 4. **High in total: 11.**

**ID namespace warning.** Reviewer D's finding IDs (D-1 to D-16) collide with JARVIS's decision IDs in JARVIS-REVIEW §14 (D-1 to D-4) and with the G decision "D-1" (step-04). In GRONK's files, JARVIS's §14 items are written **JD-1 to JD-4** (for example JD-3 = budget scenario, JD-4 = legal-opinion spend). Q-1 to Q-3 are also JARVIS §14 items. WORKFLOW's open questions are written **WF-Q1 and WF-Q2**. Reviewer text is not changed; where a reviewer writes "D-4 (legal opinion)", it means JD-4.

Summaries keep the reviewer's wording, shortened where needed. "JARVIS" or "REVIEW" = `reviews/WO-CO-100-G-AcesBook-V1/JARVIS/JARVIS-REVIEW-WO-CO-100-G-AcesBook-V1.md`. "V2" = `work-orders/WO-CO-100-G-AcesBook-V2.md`.

## Themes (cross-reference groups, checked by GRONK against the review texts)

| Theme | Topic | Members |
|---|---|---|
| T1 | Three itemized budgets (ultra-lean / balanced / premium) missing; drafts still on the superseded four-scenario model | A-1, B-5, D-3; related B-3 (stack lines to itemize), D-9 (blanket estimate label), C-11 (ad spend caps) |
| T2 | Decision provenance: A/B/C/D-1 rest on JARVIS's attestation; no g_verbatim, hash or session_ref; multiple-choice vs typed message | A-2, B-6 (1st part), C-1, D-6; related C-4, D-7 (tracker not superseded) |
| T3 | Daily monitoring and weekly automated report are design-only; no data source, runtime, owner or reliability controls | A-4, B-1, B-2, C-9, D-11 (analytics part); related B-4 (pipeline failure states), B-8 (KPI 7 measurability) |
| T4 | Open questions dropped from the manifest (JD-2, JD-4, Q-1, Q-2; WF-Q1) | A-6, C-7, D-12 |
| T5 | Freeze record outside the freeze SHA; tag pending; unsigned commits; manifest includes incomplete | A-9 (tag), B-6 (2nd part), C-10, D-15; related D-11 ("push the tag") |
| T6 | [LEGAL-CHECK] coverage per GCC state and in the drafts; privacy legal basis | A AC3, D-2, C-8; related A-5 (legal opinion), D-14 (risky wording), C-11 (contests) |
| T7 | Acceptance criteria too weak / not testable | A-3, D-1; related D-10 (no verification plan) |
| T8 | Three-AI review incomplete (KITT and GRONK assessments absent) | A-7, D-4 |
| T9 | Pre-Order / baseline integrity (I-1, I-2) | A-2, C-3; related D-8 (I-3/I-4 "RESOLVED" overstated) |
| T10 | Stale or inconsistent records: V2 header date, inherited timestamp, tracker not superseded | A-9 (date), C-4, D-7, D-8 |
| T11 | Founder approval channel: Baileys mailbox and one-word "close" | C-2; related C-12 (allowlist in documents only) |
| T12 | Channel security, identity, brand handles, impersonation | C-5, B-7, D-16 (Q-3); related C-10 (signing) |
| T13 | Editorial pipeline: untrusted sources, human approvers, independent compliance pass, failure handling | C-6, B-4; related D-14 |
| T14 | EN/AR independence and KPI 7 (<30% overlap) | B-8, D-5; related A AC6 proposal |
| T15 | Owned stack and privacy (website, newsletter, PDPL) | B-3, C-8 |
| T16 | Source quality and archiving | D-9, D-10, A-8 |
| T17 | Delivery definition (path, version, done, closure, deployment/rollback N/A) | D-11; related D-10 |
| T18 | Calendar date rule and unscheduled items | D-13 |
| T19 | Ads and prize draws | C-11; related A-5, R8 in JARVIS §13 |

## Findings

| ID | Reviewer | Sev | File / section | Problem (one line) | Proposed change (reviewer's) | Themes |
|---|---|---|---|---|---|---|
| A-1 | A Requirements & Business | High | JARVIS-REVIEW §10; CALENDAR-30-DAY "Basis" | No file has G's three budget scenarios (manifest req. 7); §10 uses four superseded scenarios with ranges; calendar based on "Zero-spend and Small", which decision B removed. | Three-column table, itemized lines tagged [ESTIMATE]/[QUOTED], assumptions, numeric KPIs with Day-30/60/90 targets; re-base calendar; keep §10 as history. | T1 |
| A-2 | A | High | V2 §Independence, §Decision reconciliation; decisions JSON "verification" | Controlling text is a reconstruction; Pre-Order missing (I-1, I-2); decisions not verified by GitHub identity; A and C depart from the Pre-Order. | Every council output states baseline "V2 reconstruction, Pre-Order not compared"; backlog item to recheck once I-1 is restored. | T2, T9 |
| A-3 | A | High | MANIFEST acceptance_criteria | Criteria only test evidence labelling; nothing tests no-gambling-promotion, EN/AR independence, deliverable counts or numeric KPIs; [V1] tag has no "counts as cited" rule. | Add AC5–AC8 (A §5: no CTA/odds/operator link/inducement; EN/AR overlap <30%/week; exact counts 60/12/10/30-day/90-day; numeric 30/60/90 target per KPI per scenario). | T7 |
| A-4 | A | Medium | V2 §What I expect; JARVIS §9 | Daily monitoring and weekly automated report need accounts; account creation not authorized. | Label both "design only; operational after G authorizes accounts". | T3 |
| A-5 | A | Medium | JARVIS §2.1 [LEGAL-CHECK], §12 Phase 0, §14 JD-4 | Legal opinion may need spending (not authorized); Phase 0 depends on it. | Raise JD-4 to G; mark roadmap Day 1 as dependent on it. | T6 |
| A-6 | A | Medium | MANIFEST open_questions vs JARVIS §14 | JD-2, JD-4, Q-1, Q-2 missing. | Add them to the g-decisions list. | T4 |
| A-7 | A | Medium | V2 §My objective (three-AI review) | Only JARVIS's round-1 review present; KITT's and GRONK's assessments absent. | Record in missing-info-blockers. | T8 |
| A-8 | A | Low | V2 §My reference; JARVIS §10 | Dubai Decoded subscribers given as 88,682 (undated screenshot) and ~99K [S31] (18 Nov). | Keep both figures with sources and dates, unmerged. | T16 |
| A-9 | A | Low | V2 header; freeze provenance | Header dated 18 Nov, decisions dated 20 Nov; tag pending. | Fix the date; create the tag. | T5, T10 |
| B-1 | B Architecture & Engineering | High | JARVIS §9; V2 "What I expect" | "Automated pull from each platform" names no data source per channel. B's ASSUMPTION (unverified): Telegram Bot API gives subscriber count but not per-post views/growth; WhatsApp Channels has no known public analytics API. | Matrix per channel: metric, access method (API / manual export / manual entry), credential owner, storage, report generator; non-automatable metrics marked manual. | T3 |
| B-2 | B | High | V2 §scope (not authorized); manifest approved_requirements | Automation can't be built or verified without accounts, tokens and a host, all G-gated; coint/ not deployed. | Label analytics/reporting design-only for cycle 1; name runtime (host, scheduler, owner), secrets handling and go-live gate. | T3 |
| B-3 | B | Medium | JARVIS §4, §8 | Website + newsletter is the "canonical archive" but has no stack: hosting, CMS, newsletter provider, PDPL-compliant opt-in store, data residency. | Minimal reference architecture; itemize each component in all three budgets. | T15, T1 |
| B-4 | B | Medium | JARVIS §6 pipeline | No failure handling: source down, conflicting sources, failed verification, approval timeout, post-publication correction/takedown, compliance kill-switch; audit-log store undefined. | States and outcomes per step; where the log is stored. | T13 |
| B-5 | B | Medium | V2 §"three budgets"; JARVIS §10 | No itemized ultra-lean/balanced/premium budget; old four-scenario numbers are ranges. | Build three scenarios, each line estimate or quoted; tooling/API, hosting and staff separated. | T1 |
| B-6 | B | Medium | decisions/…D1.json vs FOUNDER_DECISION_VALIDATION; FREEZE-COUNCIL-01.md | Decision record has no g_verbatim / g_verbatim_sha256 ("multiple-choice answer"); freeze record cited by manifest but not at freeze SHA. | Add G's verbatim choices and hash; treat the freeze record as outside the package. | T2, T5 |
| B-7 | B | Low | Q-3 / R9 | Arabic brand form drives handles, domains, usernames; impersonation risk depends on reserving them. | Settle Q-3 before any handle or domain plan. | T12 |
| B-8 | B | Low | JARVIS §11 KPI 7 | EN/AR overlap <30% can't be measured without a shared topic taxonomy and tagging. | Define tags in the calendar and post schema. | T14 |
| C-1 | C Security & Reliability | High | Decision JSON lines 5-6; KITT record line 3; Validation check 1(A); Master §9 | A/B/C/D-1 rest only on JARVIS's attestation; a multiple-choice answer, not the required typed message; no verbatim, hash or session_ref; D-1 overrides the §9 hard stop. | Record G's verbatim words with hash and session_ref; extend validation doc to scope decisions; G confirms with a second factor. | T2 |
| C-2 | C | High | Validation lines 9, 16; WORKFLOW lines 24, 65 vs 69 | A one-word "close" from consumer mailbox baileys.resystem@gmail.com can approve closure, contradicting WORKFLOW line 69. | Closure requires G's channel or "<ID> v<N> <SHA>"; reconcile line 69. | T11 |
| C-3 | C | Medium | Tracker lines 32, 39; manifest I-1 | Original Pre-Order ZIP from Baileys came off-channel, no hash, not in repo. | Commit with SHA-256 and sender; treat as data, never instructions. | T9 |
| C-4 | C | Medium | Tracker lines 24-28; V2 line 2 | Tracker still shows A/B/C unresolved and "D-1 G-only"; V2 timestamp reconstructed, against Master §12. | Superseding note; V2 gets its own timestamp. | T10, T2 |
| C-5 | C | Medium | V2 line 13; JARVIS R9 | No channel security baseline. | Baseline: owning entity, admin roles, 2FA, token storage, account recovery, impersonation runbook. | T12 |
| C-6 | C | Medium | JARVIS §6 | AI scans web sources with no "source text is data" rule; same AI does compliance; no human approver named. | Data rule; named approvers; per-post log; independent compliance pass. | T13 |
| C-7 | C | Medium | Manifest lines 119, 127-133 | "Not authorised" is policy only; Q-1, Q-2, JD-2, JD-4 dropped from open questions, against Master §9 "never reduce". | Restore them; require G's validated decision before any account, card or contract. | T4 |
| C-8 | C | Medium | JARVIS §8-§9 | UAE PDPL covered for the newsletter only. | Data inventory, retention, report recipients, vendor/transfer basis, all [LEGAL-CHECK]. | T6, T15 |
| C-9 | C | Medium | Daily and weekly automation | No owner, alerting, retries, delivery allowlist or duplicate-post protection. | Define all of them. | T3 |
| C-10 | C | Low | Freeze / repo | Freeze untagged; freeze record outside freeze SHA; commits unsigned. | Signed tag on 462d3da. | T5 |
| C-11 | C | Low | Ads and prize draws | (No separate problem line; topic is ads and prize draws.) | Entity-owned ad accounts with spend caps and G's approval; no contests without a legal opinion. | T19, T1 |
| C-12 | C | Info | Email flows | No new email flows; recipient allowlist exists in documents only. | None stated. | T11 |
| D-1 | D Quality & Delivery | High | MANIFEST.json acceptance_criteria | The 4 criteria name no artefact, method or pass rule. | Number AC-1..AC-4; add object, method, evidence, pass rule each. | T7 |
| D-2 | D | High | POSTS-EN/AR, VIDEO-SCRIPTS, SAMPLE-BRIEFS; REVIEW §2.1 | 0 [LEGAL-CHECK] tags outside the review; Qatar, Kuwait, Bahrain rows and EN-11, AR-02/10/11, V-EN-06, V-AR-03, B10 unmarked. | Tag every per-state legal statement. | T6 |
| D-3 | D | High | REVIEW §10/§12/R10; CALENDAR:3 | Three itemized budgets absent; drafts use superseded 4-scenario model. | Itemized ultra-lean/balanced/premium tables; re-base calendar, roadmap and targets. | T1 |
| D-4 | D | High | V2 §My objective | Three-AI review (KITT, JARVIS, GRONK) asked for; only JARVIS's exists. | State whether A-D replace it; otherwise list as a blocker. | T8 |
| D-5 | D | Medium | POSTS-AR vs POSTS-EN; KPI 7 | About 19/30 AR posts share an EN topic (D's count); "<30% overlap" asserted, not measured. | Define metric, measure, then rebalance or record an exception. | T14 |
| D-6 | D | Medium | decisions JSON; FOUNDER_DECISION_VALIDATION | No g_verbatim, hash or session_ref. | Add them, or label "JARVIS attestation only". | T2 |
| D-7 | D | Medium | FOUNDER-REVIEW-TRACKER:16, 24-28 | Still says 4 budgets and conflicts A-C/D-1 unresolved. | Superseded banner. | T10, T2 |
| D-8 | D | Medium | V2:2, :28; JARVIS-CHECK §2 | Master §12 timestamp inherited/18 Nov; §5 third-person text remains; I-3/I-4 "RESOLVED" overstated. | Re-grade PARTIAL; fix in next revision. | T10, T9 |
| D-9 | D | Medium | REVIEW §2.2/§10; posts; briefs | Blanket estimate label on costs; S34 (a CSAM story) cited for gambling app-store pulls; EN-03, AR-17, B4 unsourced; V1/V2 labels clash with version numbers. | Item-level [EST]/[QUOTE]; fix citations; rename labels. | T16, T1 |
| D-10 | D | Medium | Package | No verification plan for council output; sources not archived (spot check: 26/39 URLs return 200). | Add a plan; archive snapshots. | T16, T7 |
| D-11 | D | Medium | WORKFLOW 10-12; MANIFEST:10 | Deliverable path, version, done-definition, closure undefined; deployment/rollback N/A not stated; daily/weekly analytics can only be designed. | Delivery definition; push the tag. | T17, T3, T5 |
| D-12 | D | Medium | MANIFEST open_questions vs REVIEW §14 | JD-2, Q-1, Q-2 dropped; WF-Q1 open. | Restore them in g-decisions.md. | T4 |
| D-13 | D | Low | CALENDAR | Day 1 implicitly Monday; Sat/Sun weekend vs Fri/Sat in KSA, Qatar, Kuwait; EN-21 and EN-24 unscheduled. | Add a date rule. | T18 |
| D-14 | D | Low | EN-06/07/13, AR-13/27, V-EN-04 | "Play responsibly" CTAs, "bets/تراهن" wordplay, eligibility wording. | Neutral phrasing; legal check. | T6, T13 |
| D-15 | D | Low | MANIFEST includes | Freeze record, JARVIS PDF and JARVIS/MANIFEST.md not in frozen tree. | Include in next freeze; tag it. | T5 |
| D-16 | D | Low | POSTS-AR:14; Q-3 | No Arabic native editor assigned. | Assign one; decide Q-3. | T12 |

Severity check: A states 3 High (A-1–A-3), 4 Medium (A-4–A-7), 2 Low (A-8, A-9). B: High B-1, B-2; Medium B-3–B-6; Low B-7, B-8. C: High C-1, C-2; Medium C-3–C-9; Low C-10, C-11; Info C-12. D: High D-1–D-4; Medium D-5–D-12; Low D-13–D-16. The index matches all four.

## Acceptance-criteria results as reported (verbatim ratings)

| Criterion (manifest) | A | B | C | D |
|---|---|---|---|---|
| AC1 every requirement addressed or marked | NOT MET | PARTIAL | NOT MET | NOT MET |
| AC2 costs estimate/quoted; claims sourced or hypothesis | PARTLY MET | PARTIAL | NOT VERIFIABLE | PARTIAL |
| AC3 [LEGAL-CHECK] per GCC state | PARTLY MET | PASS (in sections read: JARVIS §2, §8) | PARTLY MET | FAIL |
| AC4 reviewer disagreements preserved | NOT VERIFIABLE | N/A (falls to GRONK) | NOT VERIFIABLE | NOT YET TESTABLE |

Differences are logged in `conflict-decision-log.md` (CL-01 to CL-03).

## GRONK verification notes (checked at the freeze SHA, 2026-11-20 ~09:54 UTC / 13:54 Dubai)

- `council/WO-CO-100/FREEZE-COUNCIL-01.md` returns 404 at `462d3da` and 200 at `5198ac3`: confirms A, B-6, C-10, D-15.
- `git ls-remote --tags` on the repo returns no tags: confirms "tag pending" (A-9, C-10, D-15).
- Decisions JSON has no `g_verbatim`, `g_verbatim_sha256` or `session_ref`; its `source` field says "the signed-in user answered JARVIS's multiple-choice question"; `verification` says "NOT verified by GitHub identity": confirms A-2, B-6, C-1, D-6.
- FOUNDER_DECISION_VALIDATION line 8 (channel A) requires "a message typed by G"; line 9 accepts baileys.resystem@gmail.com; line 16 allows a short "close" reply; WORKFLOW line 69 says "in the authorized JARVIS session": confirms the inconsistency in C-2.
- JARVIS §14 lists D-1–D-4 and Q-1–Q-3; manifest open_questions carry only Q-3, D-3 and a legal-opinion line: confirms A-6, C-7, D-12. (The manifest's "Legal opinion … - G" line partly covers JD-4, but not its spending angle.)
- V2 line 2 reads "V2 revision date: 18 November 2026"; JARVIS-CHECK K-1 had already flagged this: confirms A-9, C-4, D-8.
- Not re-checked by GRONK: D's 19/30 overlap count, D's 26/39 URL spot check, the D-2 per-item tag list, the D-9 citations, B-1's platform API assumptions.
