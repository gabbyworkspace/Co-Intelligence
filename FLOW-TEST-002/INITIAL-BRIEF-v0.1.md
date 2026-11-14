# FLOW-TEST-002 — Initial sample project brief v0.1

**Status:** PROPOSED / AWAITING FOUNDER INITIAL BRIEF CONFIRMATION. This is KITT's draft based on G's instruction: "Okay, create another sample project and do the flow test, everything." This instruction authorizes starting the sample project; it is not approval of this detailed brief, a Council decision, or Step 11 final delivery approval.

## Purpose
Run a fresh end-to-end Co-Intelligence workflow exercise, independently of FLOW-TEST-001, using the real roles and gates defined in WORKFLOW.md v2.0. Do not reuse old test results as new-run evidence.

## Sample deliverable
A standalone, dependency-free HTML checklist at `deliveries/FLOW-TEST-002/v1/index.html`, titled **Sample Project Checklist**. On load, show three tasks: "Review brief", "Complete build", "Verify handoffs", each initially unchecked; show a counter `0 of 3 complete`. Toggling a checkbox updates the counter immediately. When all three are checked, show exactly `All sample tasks complete.`; if one is unchecked again, remove that completion message. No external resources, analytics, storage, remote network requests or actual AI agents. Use safe DOM updates (textContent) and restrictive CSP.

## Acceptance checks
- Initial rendering has exactly three unchecked checklist items, matching labels and 0/3 counter.
- Each toggle updates count correctly for 0,1,2,3 and back to 2.
- Completion message appears only when all three are checked; disappears on reversal.
- Keyboard operation works and labels are associated with checkboxes.
- No network calls or external dependencies; no console errors; restrictive CSP.
- JARVIS records actual test commands, environment, timestamps, artifacts, commit SHAs, and results. KITT independently reviews the delivered source and evidence after JARVIS handoff.

## Workflow exercise and evidence
- Step 1: G reviews this draft in KITT chat. **Do not advance past founder brief confirmation until explicit approval of this brief is recorded.** Once confirmed, KITT sends initial review email to baileys.resystem@gmail.com through authorized KITT integration, if available, and records Gmail acceptance separately from receipt.
- Steps 2–4: KITT hands off approved brief to JARVIS via GitHub. JARVIS reviews; KITT revises with traceable findings and frozen version.
- Steps 5–7: JARVIS freezes a manifest and SHA, GRONK coordinates four genuinely independent reviewer returns, JARVIS reconciles; material decisions return to G. No simulated reviewer attestations.
- Steps 8–10: JARVIS builds/tests, KITT independently reviews, JARVIS dispositions findings and freezes exact delivery SHA/tag.
- Step 11: JARVIS presents exact final version in authorized JARVIS chat, sends review package to baileys.resystem@gmail.com **and g@resystem.org** per G's latest additional-recipient instruction (dedupe per recipient), validates G's explicit final decision for exact version; KITT records it.
- Step 12: only after all closure gates, JARVIS creates closure evidence and sends the final report once to g@resystem.org.

## Additional automation acceptance
Record actual webhook/event pickup, duplicate-event replay and recovery run evidence if PR #1 automation engine becomes live. Until then, C17–C19 remain BLOCKED, never PASS; do not claim a full autonomous end-to-end success. If G explicitly approves partial closure for FLOW-TEST-002, record that exact decision; FLOW-TEST-001's exception does not automatically authorize a new project exception.

## Non-goals / restrictions
No deployments, permissions or production changes, no purchases, no synthetic approvals, no email send claims without Gmail IDs, no impersonation of JARVIS/GRONK/reviewers. Existing project records remain untouched.

## Next gate
**Owner G:** confirm or amend this initial brief. **Owner KITT after confirmation:** record G's exact words, publish approved v1.0, initiate JARVIS review, and follow WORKFLOW.md. This draft is deliberately not a completed project.
