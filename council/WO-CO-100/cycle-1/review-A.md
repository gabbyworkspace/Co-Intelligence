<!-- Received by GRONK via agent message from Council reviewer A (009caf62-b180-4758-a06f-1bfe1ce8e43b) at 2026-11-20 ~09:47Z (13:47 Dubai). Saved verbatim. -->
COUNCIL REVIEW A: Requirements and Business

1. HEADER
Reviewer A, working independently; I read no other reviewer's output. Package WO-CO-100-C1-COUNCIL-01, project WO-CO-100 (AcesBook GCC), cycle 1. Freeze SHA 462d3da2fc2e4764a52d4c2eb99b7c500aeec644. Read 2026-11-20 09:44:57Z, which is 13:44 Dubai.
Integrity: the manifest blob is 42e568b7, and all 19 listed blobs match at the freeze SHA. FREEZE-COUNCIL-01.md is NOT in the freeze commit; it was added in 5198ac3, and I read it there. The freeze tag is still pending.

2. VERDICT: PASS WITH CHANGES
The package is readable and traces back to the work order. However, the three-budget requirement has no deliverable, AC1 is not met, and launch-critical dependencies sit with G.

3. FINDINGS
A-1 High. Files: JARVIS-REVIEW §10 and CALENDAR-30-DAY "Basis". Problem: no file contains G's three budget scenarios (ultra-lean, balanced, premium; manifest requirement 7). §10 still uses the four superseded scenarios with monthly ranges, not itemized costs, and the calendar is based on "Zero-spend and Small", which decision B removed. Change: add a three-column table with itemized lines tagged [ESTIMATE] or [QUOTED], assumptions, and numeric KPIs with Day-30/60/90 targets. Re-base the calendar on those scenarios and keep §10 unchanged as history.
A-2 High. Files: V2 work order §Independence and §Decision reconciliation; decisions JSON "verification". Problem: the controlling text is a reconstruction, the Pre-Order is missing (I-1, I-2), the decisions are not verified by GitHub identity, and decisions A and C depart from the Pre-Order. Change: every council output should state its baseline as "V2 reconstruction, Pre-Order not compared". Add a backlog item to recheck once I-1 is restored.
A-3 High. File: MANIFEST acceptance_criteria. Problem: the criteria only test how evidence is labelled. Nothing tests the no-gambling-promotion rule, whether the EN and AR streams are independent, the deliverable counts, or numeric KPIs. The [V1] tag ("second source needed") has no rule for whether it counts as cited. Change: add AC5–AC8 (see section 5).
A-4 Medium. Files: V2 §What I expect and JARVIS §9. Problem: daily monitoring and the weekly automated report need accounts, and creating accounts is not authorized. Change: label both "design only; operational after G authorizes accounts".
A-5 Medium. Files: JARVIS §2.1 [LEGAL-CHECK], §12 Phase 0 and §14 D-4. Problem: a legal opinion may need spending, which is not authorized, and Phase 0 depends on that opinion. Change: raise D-4 to G and mark Day 1 of the roadmap as dependent on it.
A-6 Medium. File: MANIFEST open_questions, compared with JARVIS §14. Problem: D-2, D-4, Q-1 and Q-2 are missing. Change: add them to the g-decisions list.
A-7 Medium. File: V2 §Objective (three-AI review). Problem: only JARVIS's round-1 review is present; KITT's and GRONK's assessments are absent. Change: record this in missing-info-blockers.
A-8 Low. Files: V2 §My reference and JARVIS §10. Problem: Dubai Decoded subscribers appear as both 88,682 (undated screenshot) and ~99K [S31] (18 Nov). Change: keep both figures with their sources and dates, unmerged.
A-9 Low. Files: V2 header and freeze provenance. Problem: the header is dated 18 Nov while the decisions are dated 20 Nov, and the tag is pending. Change: fix the date and create the tag.

4. ACCEPTANCE CRITERIA
AC1 (every requirement addressed or marked): NOT MET. Requirement 7 (budgets) is missing, requirement 5 (automated reporting) is not marked design-only, and the channel assessment is JARVIS's alone.
AC2 (costs marked estimate or quoted; claims sourced or labelled hypothesis): PARTLY MET. §10 is labelled at section level, not line by line, and is superseded. I did not verify source IDs across the 60 posts, 12 scripts and 10 briefs.
AC3 ([LEGAL-CHECK] per GCC state): PARTLY MET. Tags are at section level; Qatar, Kuwait and Bahrain rest on secondary sources and aren't tagged individually. There are 0 tags in the posts and scripts, although 11 AR posts cover regulation and law.
AC4 (reviewer conflicts preserved): NOT VERIFIABLE. The council outputs don't exist yet. The tracker does preserve conflicts A, B and C.

5. G DECISIONS
(1) D-3: which budget scenario runs the first 90 days. This comes after A-1 is done.
(2) Q-3: how the brand appears in the Arabic stream; AR items currently use "AcesBook GCC".
(3) D-4: whether to authorize a legal opinion, which may involve spending.
(4) D-2, Q-1 and Q-2: editorial red lines, who approves posts in each stream, and which entity and jurisdiction own the channels.
(5) Whether G confirms decisions A–D-1 in G's own words or through GitHub, which would close A-2.
(6) Whether to adopt these new criteria: AC5, no CTA, odds, operator link or inducement in any item; AC6, EN/AR topic overlap below 30% per week; AC7, exact deliverable counts (60/12/10/30-day/90-day); AC8, a numeric 30/60/90 target for every KPI in each scenario.

6. MISSING INFO AND BLOCKERS
The Pre-Order and the canonical ZIP/PDF (I-1, I-2) are absent, so comparison against the source is BLOCKED. The Dubai Decoded screenshots and MP4 are absent, so media analysis is BLOCKED and moved to round two. G's verbatim decisions are not available; JARVIS attests them alone. KITT's and GRONK's assessments are absent. The freeze record only exists after the freeze commit, and the tag is pending. Not verified by me: the S1–S38 links, the market and legal facts, and the source tags on each post.

Not approved on G's behalf. Repo unchanged; for GRONK to publish at council/WO-CO-100/cycle-1/review-A.md.
