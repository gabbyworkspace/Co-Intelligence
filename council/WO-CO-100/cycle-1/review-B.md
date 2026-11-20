<!-- Received by GRONK via agent message from Council reviewer B (d8cb579e-5de1-4df7-9019-cd893801eeec) at 2026-11-20 ~09:46Z (13:46 Dubai). Saved verbatim. -->
# review-B — Reviewer B (Architecture and Engineering)
Package WO-CO-100-C1-COUNCIL-01 · Freeze SHA 462d3da2fc2e4764a52d4c2eb99b7c500aeec644
Read: 2026-11-20 09:44–09:46 UTC (13:44–13:46 Dubai). All 19 manifest blobs were re-hashed (git hash-object) and all match. Independent first pass; I have not seen any other review.

## Verdict: PASS WITH CHANGES
The concept is technically feasible. However, the monitoring/reporting automation and the owned-channel stack are specified only as intent, and the three-scenario budget doesn't exist yet.

## Findings
- **B-1 High.** File: JARVIS-REVIEW §9; V2 "What I expect". Problem: "Daily monitoring + weekly automated report" assumes an "automated pull from each platform", but no data source is named for each channel. ASSUMPTION, to be verified: the Telegram Bot API exposes the subscriber count but not per-post views or growth stats (those need in-app Statistics or an MTProto user session); WhatsApp Channels has no known public analytics API. Change: add a matrix with one row per channel covering metric, access method (API / manual export / manual entry), credential owner, storage location, and the report generator. Any metric that can't be pulled automatically should be marked manual.
- **B-2 High.** File: V2 §scope (not authorized: accounts, spending); manifest approved_requirements. Problem: the automation can't be built or verified without accounts, API tokens and a host to run on, and all of those are G-gated. coint/ isn't deployed either. Change: label the analytics and reporting as design-only for cycle 1, and name the runtime (host, scheduler, owner), the secrets handling and the go-live gate.
- **B-3 Medium.** File: JARVIS §4 and §8. Problem: the website plus newsletter is meant to be the "canonical archive", but there's no stack: hosting, CMS, newsletter provider, a PDPL-compliant opt-in data store and data residency are all missing. Change: add a minimal reference architecture, and itemize each of those components in all three budgets.
- **B-4 Medium.** File: JARVIS §6 pipeline. Problem: there's no failure handling for a source that's down, conflicting sources, a failed verification, an approval timeout, correction or takedown after publishing, or a compliance kill-switch. The audit-log store is also undefined. Change: add states and outcomes for each step, plus where the log is stored.
- **B-5 Medium.** File: V2 §"three budgets"; JARVIS §10 (superseded by decision B). Problem: no ultra-lean/balanced/premium budget with itemized costs exists in the package, and the old four-scenario numbers are ranges, not line items. Change: build the three scenarios with each line marked estimate or quoted, with tooling/API, hosting and staff costs separated out.
- **B-6 Medium.** File: decisions/…D1.json vs FOUNDER_DECISION_VALIDATION. Problem: the decision record has no g_verbatim or g_verbatim_sha256 field ("multiple-choice answer"). FREEZE-COUNCIL-01.md is cited by the manifest but isn't at the freeze SHA (it was added later). Change: add G's verbatim choices and hash to the decision record, and treat the freeze record as outside the package.
- **B-7 Low.** File: Q-3 / R9. Problem: the Arabic brand form determines handles, domains and channel usernames, and impersonation risk depends on reserving them. Change: settle Q-3 before any handle or domain plan.
- **B-8 Low.** File: JARVIS §11 KPI 7 (EN/AR overlap below 30%). Problem: this can't be measured without a shared topic taxonomy and tagging. Change: define the tags in the calendar and post schema.

## Acceptance criteria
1. Every requirement addressed: PARTIAL. Channels, streams, red lines, the 60 posts (counted 30 EN and 30 AR), 10 briefs, a 30-day calendar and a 90-day roadmap are present as round-1 drafts. The three budgets are missing (B-5), and automation is design-only (B-1, B-2). I didn't count the video scripts individually.
2. Costs marked estimate or quoted, and claims sourced: PARTIAL. Costs are labelled as estimates but aren't itemized. Sources S1–S38 exist with weak sources flagged; I didn't re-verify each claim.
3. [LEGAL-CHECK] marking: PASS in the sections I read (JARVIS §2 and §8). It wasn't checked line by line in the posts.
4. Conflicts preserved: N/A for a single reviewer; this falls to GRONK's log.

## Needs G
D-3 (which scenario), Q-3 (Arabic brand), D-4 (legal opinion spend), Q-1 (human approver for each stream), Q-2 (owning entity, which also determines who owns the platform accounts and API credentials), and when accounts may be created so that analytics can be built.

## Missing info / blockers
The Pre-Order (I-1/I-2); the Dubai Decoded media (round two); confirmation of what each platform's analytics access actually allows; hosting and stack choices.
