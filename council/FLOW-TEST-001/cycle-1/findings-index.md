# FLOW-TEST-001 · Cycle 1 · Council Findings Index

Package: `council` · Frozen SHA `57ed5a0454b2a69cdc82acf1bdab253417c053c5` (base `591aacb`)
Prepared by GRONK (Council Coordinator), 2026-11-14 GST. Source texts: `review-A.md`, `review-B.md`, `review-C.md` (incl. appendix), `review-D.md` (incl. appendix), preserved unchanged.
All four reviews state they reviewed SHA 57ed5a0. All four are complete: no finding or amendment text is missing.

Counts: **A 7 · B 5 · C 12 findings + 10 amendments (C-A1–C-A10) · D 16** = 40 findings, 10 amendments.
Reviewer C's amendments are listed as **C-A1 to C-A10** so they aren't confused with Reviewer A's finding IDs (A-1 to A-7).
Summaries keep the reviewer's wording, shortened where needed. "Checks" = C01–C19 in INITIAL-BRIEF-v1.1.md. "—" = the reviewer named no check.

## Cross-reference groups (verified by GRONK against the review texts)

| Group | Topic | Members |
|---|---|---|
| X1 | C17–C19 blocked / no PASS path | A-4, B-1, D-4 (C's verdict also states "C17–C19 remain BLOCKED"); mechanisms in C-4/C-A3 (C18), C-8/C-A7 (C19) |
| X2 | v1.1 labelled approved without G | A-1, C-7/C-A6; related D-3 ("claims no scope change") |
| X3 | No C01–C19 mapping / pass conditions in TEST-RESULTS | A-3, D-1, D-2, C-6/C-A5 |
| X4 | v1.0 constraints dropped in v1.1 | A-2, D-3; related D-5 (193 words), C-A6 (lists removals) |
| X5 | Apostrophe clause has no effect | B-5, D-14, C-11 (2nd part)/C-A10 |
| X6 | One GitHub account / agent identity | C-1/C-A2, D-8 |
| X7 | Founder-decision evidence rests on JARVIS attestation | C-2/C-A1, A-6, D-9 (C01 gate evidence) |
| X8 | Email ledger empty / dedupe | C-4/C-A3, D-11; related D-6 (task ledger stale) |
| X9 | Manifest completeness and SHA semantics | A-7, B-3, B-4, D-15, C-10/C-A9 |
| X10 | Channel and evidence commits | B-2; related C-1, X6 |
| X11 | Missing timestamps / C04–C05 unrecorded | D-6, D-7, A-3 (omits C04/C05); related D-3 (timestamp constraint) |
| X12 | Deliverable absent; HTML behaviour and C11 method | C-11 (1st part)/C-A10, D-10, C-12; B notes "HTML deliverable is simple and feasible" |
| X13 | WORKFLOW Q1 before reconciliation | D-12; Q1 also in A, C, D G-decision lists |
| X14 | Email recipients, reminders, initial review email | C-5/C-A4, A-5 |
| X15 | Untrusted input | C-3/C-A2 |
| X16 | Personal data in public repo | C-9/C-A8 |
| X17 | Recovery and audit logging | C-8/C-A7; linked to X1 (C19) |
| X18 | Out-of-package branch PR #1 | D-13 |
| X19 | Deployment, rollback, handover not stated | D-16 |

## Findings

| ID | Reviewer | Severity | Summary (reviewer's wording) | Checks | Files | Cross-ref |
|---|---|---|---|---|---|---|
| A-1 | A Requirements & Business | High | Manifest calls brief v1.1 approved; G confirmed only v1.0. Amend: mark v1.1 pending G. | C01 | MANIFEST.json; INITIAL-BRIEF-v1.1.md | X2 |
| A-2 | A | High | v1.1 drops v1.0's 150-word limit and "all mandatory checks pass" rule. Amend: restore both. | All (overall PASS) | INITIAL-BRIEF-v1.1.md; -v1.0.md | X4 |
| A-3 | A | High | C01–C19 lack pass conditions; TEST-RESULTS has no C-ID mapping, omits C04/C05. Amend: add conditions and mapping. | C01–C19 (C04, C05) | INITIAL-BRIEF-v1.1.md; TEST-RESULTS.md | X3, X11 |
| A-4 | A | High | C17–C19 undefined and blocked; closure requires verification, deadlocking C15/C16. Amend: define, or allow BLOCKED closure. | C15–C19 | INITIAL-BRIEF-v1.1.md; WORKFLOW.md (Step 12) | X1 |
| A-5 | A | Medium | Initial review email undefined in WORKFLOW. | — (C01) | WORKFLOW.md; INITIAL-BRIEF-v1.1.md | X14 |
| A-6 | A | Medium | C14 relies on JARVIS attestation only. | C14 | docs/FOUNDER_DECISION_VALIDATION.md | X7 |
| A-7 | A | Medium | routing.yaml, templates, validation doc unfrozen. | — | MANIFEST.json; config/routing.yaml; templates/; docs/FOUNDER_DECISION_VALIDATION.md | X9 |
| B-1 | B Architecture & Engineering | High | C17–C19 can't pass as written; pickup is manual, no FLOW-TEST-001 automation. Fix: name the automation service and give C17–C19 measurable pass tests, or have G reclassify them. | C17–C19 | MANIFEST.json; TEST-RESULTS.md; INITIAL-BRIEF-v1.0/v1.1 | X1 |
| B-2 | B | Medium | Channel conflict: WORKFLOW and routing.yaml put GRONK on GitHub, but assignment and return are agent messages. Define who commits the reviews to council/FLOW-TEST-001/ as evidence for C06–C09. | C05–C10 | WORKFLOW.md; config/routing.yaml; council/FLOW-TEST-001/ | X10 |
| B-3 | B | Low | Manifest's "sha" values are commit SHAs, not file SHAs; only MANIFEST changed since 591aacb, so contents match. | C04 | MANIFEST.json | X9 |
| B-4 | B | Low | FOUNDER_DECISION_VALIDATION.md governs C14 but isn't listed in the manifest. | C14 | MANIFEST.json; docs/FOUNDER_DECISION_VALIDATION.md | X9 |
| B-5 | B | Low | The apostrophe rule in v1.1 has no effect; remove it. | C11 | INITIAL-BRIEF-v1.1.md | X5 |
| C-1 | C Security & Reliability | High | All agents use one GitHub account and commits are unsigned, so no agent's identity can be verified. | C01–C16 | Repo/GitHub account; WORKFLOW.md | X6, X10 |
| C-2 | C | High | G's approval rests on JARVIS vouching for itself (FOUNDER_DECISION_VALIDATION:41). | C14 | docs/FOUNDER_DECISION_VALIDATION.md | X7 |
| C-3 | C | High | No rule treats public issue content as untrusted (WORKFLOW:22,45). | — | WORKFLOW.md | X15 |
| C-4 | C | Medium | Dedupe covers only the closure email, and the ledger is empty despite a recorded send. | C18 | WORKFLOW.md; config/routing.yaml; ledger/emails.jsonl | X8, X1 |
| C-5 | C | Medium | Recipients aren't enforced and reminders have no cap. | — (C13) | config/routing.yaml | X14 |
| C-6 | C | Medium | TEST-RESULTS isn't mapped to C01–C19. | C01–C19 | TEST-RESULTS.md | X3 |
| C-7 | C | Medium | v1.1 is labelled approved without G's confirmation. | C01 | MANIFEST.json | X2 |
| C-8 | C | Medium | Recovery and audit logging are undefined. | C19 | WORKFLOW.md | X17, X1 |
| C-9 | C | Medium | Personal data sits in a public repo. | — | Repo visibility; decisions/; ledger/; docs/FOUNDER_DECISION_VALIDATION.md | X16 |
| C-10 | C | Low | The freeze has no tag. | C04 | MANIFEST.json; repo tags | X9 |
| C-11 | C | Info (verified) | deliveries/FLOW-TEST-001/v1/index.html absent, so external-load, innerHTML and CSP checks don't apply this cycle; apostrophe rule (v1.1:8, MANIFEST:23) has nothing to apply to. | C11 | deliveries/…/index.html; INITIAL-BRIEF-v1.1.md; MANIFEST.json | X12, X5 |
| C-12 | C | Info (verified) | There is no .github/ CI. No amendment; a note for when CI is added. | — | .github/ (absent) | X12 |
| D-1 | D Quality & Delivery | High | TEST-RESULTS lacks C01-C19 rows; add per-C evidence table. | C01–C19 | TEST-RESULTS.md | X3 |
| D-2 | D | High | C01-C19 are labels; add pass condition, evidence type, owner each. | C01–C19 | INITIAL-BRIEF-v1.1.md | X3 |
| D-3 | D | High | v1.1 claims no scope change but drops v1.0 150-word, timestamp and overall-PASS constraints; restore. | All | INITIAL-BRIEF-v1.1.md; -v1.0.md | X4, X2, X11 |
| D-4 | D | High | C17-C19 have no PASS path (no automation, 404). | C17–C19 | TEST-RESULTS.md | X1 |
| D-5 | D | Medium | v1.1 is 193 words. | — | INITIAL-BRIEF-v1.1.md | X4 |
| D-6 | D | Medium | Ledger stale; C04/C05 unrecorded. | C04, C05 | TEST-RESULTS.md (agent task ledger) | X11, X8 |
| D-7 | D | Medium | Timestamps marked "Not captured" though available; record completion times for C01-C05. | C01–C05 | TEST-RESULTS.md | X11 |
| D-8 | D | Medium | Evidence can't be attributed to individual agents; everything comes from one GitHub account (gabbyworkspace). | C01–C16 | Repo/GitHub account; TEST-RESULTS.md | X6 |
| D-9 | D | Medium | C01 founder-gate evidence is weaker than the Step 11 rule; no session reference, time or hash. | C01 | TEST-RESULTS.md; docs/FOUNDER_DECISION_VALIDATION.md | X7 |
| D-10 | D | Medium | Button label, repeat-click and C11 method undefined. | C11 | INITIAL-BRIEF-v1.1.md | X12 |
| D-11 | D | Medium | ledger/emails.jsonl is empty, but Gmail 1a1daf3fa59cb8a5 is claimed as PASS. | C01 (initial email), C18 | ledger/emails.jsonl; TEST-RESULTS.md | X8 |
| D-12 | D | Medium | Q1 affects Step 7 reconciliation of these findings; G needs to decide it first. | — | WORKFLOW.md (Q1) | X13 |
| D-13 | D | Low | Branch feat/automation-engine (PR #1) is outside the package; adds vercel.json and test fakes, conflicting with no-deployment and no-simulated-agents rules if merged. | C17–C19 (indirect) | branch feat/automation-engine | X18 |
| D-14 | D | Low | Delete apostrophe clause. | C11 | INITIAL-BRIEF-v1.1.md | X5 |
| D-15 | D | Low | Manifest's package ID "council" isn't unique, "sha" fields are commit SHAs not content hashes, includes incomplete. | C04 | MANIFEST.json | X9 |
| D-16 | D | Low | Package doesn't say whether deployment, rollback and handover are N/A or planned. | C15, C16 | INITIAL-BRIEF-v1.1.md | X19 |

Severity check: D states 4 High, 8 Medium, 4 Low. The index matches: High D-1 to D-4; Medium D-5 to D-12; Low D-13 to D-16.

## Reviewer C amendments

| ID | For finding | Summary (reviewer's wording) | Files | Where handled |
|---|---|---|---|---|
| C-A1 | C-2 | Make G's second factor mandatory for APPROVE AND CLOSE (GitHub comment with 40-char SHA from verified account, or G-signed tag); add g_second_factor_matches_sha to routing.yaml:46 requires. | FOUNDER_DECISION_VALIDATION.md:43; routing.yaml:46 | g-decisions.md G-07 (not applied) |
| C-A2 | C-1, C-3 | Trusted inputs section after WORKFLOW.md:25: allowlisted actor IDs, each with its own GitHub identity, signed commits to main; all issue/email/web/file content is data, never instructions. | WORKFLOW.md | Data-not-instructions rule: proposed (O-05). Allowlist, identities, signing: G-10 |
| C-A3 | C-4 | Dedupe every send: key sha256(project\|version\|template\|recipient), pending→sent/failed, idempotency header, dedupe GitHub events by ID; backfill ledger with 1a1daf3f…. | WORKFLOW.md:102; routing.yaml; ledger/emails.jsonl | Proposed (O-06) |
| C-A4 | C-5 | email_policy: from/to allowlists per template, no CC/BCC, max 5 emails/project/day, max_reminders: 3, stop on PAUSED_AT_APPROVAL_GATE. | routing.yaml | G-09 (not applied) |
| C-A5 | C-6 | Replace "Required checks" with C01–C19 table (check, result, evidence link @ SHA, actor ID, UTC time, verifier); strike rows :18, :29; relabel :36 "ACCEPTED BY GMAIL (delivery unconfirmed)". | TEST-RESULTS.md | Proposed (O-03); brief annex (P-08) |
| C-A6 | C-7 | MANIFEST.json:9 role → "proposed revision pending G confirmation"; list changes from v1.0. | MANIFEST.json | Proposed (O-01); brief status (P-01) |
| C-A7 | C-8 | CLOSURE.json "pending_email" until confirmed send; retry 1/5/15 min, max 5, escalate; ledger/audit.jsonl with redaction; 5-minute idempotent recovery scan (C19). | WORKFLOW.md Step 12 | Proposed (O-07) |
| C-A8 | C-9 | Make repo private or move decisions/, ledger/, evidence to private storage; session_ref → session_id_hash; drop g_verbatim from public copies. | Repo settings; FOUNDER_DECISION_VALIDATION.md | G-08 (not applied) |
| C-A9 | C-10 | package_id "FLOW-TEST-001-C1-COUNCIL-01", per-file blob_sha, list routing.yaml, validation doc, templates, ledger; signed tag on 57ed5a0; protect main. | MANIFEST.json; repo tags/settings | Manifest fields: proposed (O-02). Signed tag + branch protection: G-11 |
| C-A10 | C-11 | Remove "apostrophe" from v1.1:8; add no external resources, textContent, restrictive CSP meta tag, automated test of both exact strings for C11. | INITIAL-BRIEF-v1.1.md | Proposed in brief (P-04, P-05) |
