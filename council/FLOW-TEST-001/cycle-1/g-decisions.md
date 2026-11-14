# FLOW-TEST-001 · Cycle 1 · Decisions for G

SHA `57ed5a0454b2a69cdc82acf1bdab253417c053c5`. Deduplicated by GRONK. None of these is decided or applied. GRONK does not decide or approve for G.
"Raised by" lists the reviewers who named it (G list = the reviewer's own "G decisions" / "For G" line), plus the related findings.

| # | Decision | Raised by | Related IDs | Notes |
|---|---|---|---|---|
| G-01 | Which brief controls: confirm v1.1 (or the v1.2 proposal), or keep v1.0 | A, C | A-1, C-7/C-A6, D-3 | A: "controlling brief"; C: "confirm v1.1" |
| G-02 | C17–C19: mandatory, deferred, reclassified, or closure allowed with them BLOCKED | A, B, D | A-4, B-1, D-4; C verdict | Needed before the overall-PASS rule can be met (CL-01) |
| G-03 | Word-limit scope: does 150 words cover the brief, annexes, reviews and other documents? | A | A-2, D-3, D-5, C-A6 | CL-05 |
| G-04 | WORKFLOW Q1 (channel for material-change decisions), decided before reconciliation | A, C, D | D-12 | D: "Q1 before reconciliation" |
| G-05 | WORKFLOW Q2: reminder intervals (24h KITT, 48h Baileys) | A, C, D | C-5/C-A4 | C-A4 also proposes max_reminders: 3 (see G-09) |
| G-06 | Button label (and repeat-click behaviour) | D | D-10 | D's G list names the label; D-10 also flags repeat-click |
| G-07 | Make the second factor mandatory for APPROVE AND CLOSE, and give G's GitHub username | C | C-2/C-A1, A-6 | Changes FOUNDER_DECISION_VALIDATION and routing.yaml closure requires |
| G-08 | Repo visibility: make private, or move decisions/, ledger/, evidence to private storage; hash session_ref; drop g_verbatim from public copies | C | C-9/C-A8; tension with D-9 | CL-03 |
| G-09 | Email policy: from/to allowlists per template, no CC/BCC, 5 emails per project per day, max 3 reminders, stop on PAUSED_AT_APPROVAL_GATE | C (via C-A4) | C-5/C-A4 | Governance; not in C's G list, but placed here as it changes governance |
| G-10 | Separate GitHub identity per agent, actor allowlist, signed commits to main | C (via C-A2) | C-1/C-A2, D-8 | Governance; D lists agent identities as unverified |
| G-11 | Signed freeze tag and protected main (repo settings) | C (via C-A9) | C-10/C-A9 | The unsigned manifest fields are in O-02 for JARVIS |

Total: **11 decisions.**
