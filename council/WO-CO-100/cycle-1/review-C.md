<!-- Received by GRONK via agent message from Council reviewer C (ad923fa3-2527-4c60-b31e-1988b0d5898e) at 2026-11-20 ~09:48Z (13:48 Dubai). Saved verbatim. -->
1. HEADER
Reviewer C (Security and Reliability). Package WO-CO-100-C1-COUNCIL-01. Freeze SHA 462d3da2fc2e4764a52d4c2eb99b7c500aeec644.
Read 2026-11-20 09:45–09:48 UTC (13:45–13:48 Dubai).
Integrity: the manifest blob 42e568b7 matches, and all 19 listed blobs match. The decision JSON at 5597a2d matches. FREEZE-COUNCIL-01.md is not at the freeze SHA; it's in child commit 5198ac3, and its content is consistent with the manifest.
I did not open other reviewers' files. This review is not approval on G's behalf.

2. VERDICT: PASS WITH CHANGES, as a planning package. C-1, C-2 and C-5 to C-7 must be fixed before any account, publishing or spending authorisation.

3. FINDINGS
C-1 High. Decision JSON lines 5-6, KITT record line 3, Validation check 1(A), Master §9.
Problem: G's A/B/C/D-1 decisions rest only on JARVIS's attestation. They were a multiple-choice answer, not the required typed message, and there's no verbatim text, hash or session reference. D-1 overrides the §9 hard stop.
Change: record G's verbatim words with a hash and session reference, extend the validation doc to cover scope decisions, and have G confirm with a second factor.

C-2 High. Validation lines 9 and 16; WORKFLOW lines 24 and 65 vs line 69.
Problem: a one-word "close" from the consumer mailbox baileys.resystem@gmail.com can approve closure, which contradicts line 69.
Change: closure requires G's channel or "<ID> v<N> <SHA>". Reconcile line 69.

C-3 Med. Tracker lines 32 and 39; manifest I-1.
Problem: the original Pre-Order ZIP from Baileys came in off-channel, with no hash, and isn't in the repo.
Change: commit it with its SHA-256 and sender, and treat it as data, never instructions.

C-4 Med. Tracker lines 24-28; V2 line 2.
Problem: the tracker still shows A/B/C unresolved and "D-1 G-only". V2's timestamp is reconstructed, against §12.
Change: add a superseding note and give V2 its own timestamp.

C-5 Med. V2 line 13; JARVIS R9.
Problem: there's no channel security baseline.
Change: add one covering the owning entity, admin roles, 2FA, token storage, account recovery and an impersonation runbook.

C-6 Med. JARVIS review §6.
Problem: the AI scans web sources with no rule that source text is data. The same AI does the compliance check, and no human approver is named.
Change: add that data rule, name the approvers, keep a log per post, and add an independent compliance pass.

C-7 Med. Manifest lines 119 and 127-133.
Problem: "not authorised" is policy only, and Q-1, Q-2, D-2 and D-4 were dropped from the open questions, against §9 "never reduce".
Change: restore them. Require G's validated decision before any account, card or contract.

C-8 Med. JARVIS review §8-§9.
Problem: UAE PDPL is covered for the newsletter only.
Change: add a data inventory, retention period, report recipients and the basis for vendors and transfers, all marked [LEGAL-CHECK].

C-9 Med. Daily and weekly automation.
Problem: there's no owner, alerting, retries, delivery allowlist or duplicate-post protection.
Change: define all of them.

C-10 Low. The freeze is untagged, the freeze record sits outside the freeze SHA, and commits are unsigned.
Change: add a signed tag on 462d3da.

C-11 Low. Ads and prize draws.
Change: use entity-owned ad accounts with spend caps and G's approval, and run no contests without a legal opinion.

C-12 Info. There are no new email flows. The recipient allowlist exists in documents only.

4. ACCEPTANCE CRITERIA
AC1 (every requirement addressed or marked): NOT MET. The three-scenario budget doesn't exist, and channel security, privacy and automation are thin.
AC2 (costs marked estimate or quoted): NOT VERIFIABLE. The controlling budget doesn't exist; the superseded four-scenario version is labelled as estimates.
AC3 (legal statements per GCC state marked [LEGAL-CHECK]): PARTLY MET. The UAE, Qatar, Kuwait and Bahrain rows rely on secondary sources, and only the section heading carries the marker.
AC4 (reviewer disagreements preserved): NOT VERIFIABLE. The council output doesn't exist yet.

5. NEEDS G'S DECISION
Confirm A/B/C/D-1 with a second factor. Whether Baileys' email or a one-word reply may approve closure. Q-1 (human approver). Q-2 (owning entity and jurisdiction). D-2 (red lines). D-3 (budget scenario). D-4 (legal-opinion spend). Q-3 (Arabic brand form). WORKFLOW Q1 and Q2.

6. MISSING INFO AND BLOCKERS
The original Pre-Order and the canonical ZIP/PDF aren't in the repo. The Dubai Decoded media is missing, so media review moves to round 2. The JARVIS chat can't be independently verified. There's no code at this SHA, so every control is unverified design. No legal opinion has been obtained. Branch protection and signing are unverified.

Note: I have no record that my FLOW-TEST-002 cycle 1 review was ever delivered to you. Please treat Reviewer C as missing for that cycle unless you hold a copy.
