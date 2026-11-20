# WO-CO-100 · v1 delivery · Operations, security and privacy design

**WO-CO-100 · v1 delivery · Controlling brief: V3 (09f7655aaf5ddbb8a411116718e0ce909e24bd6e) · Baseline: reconstruction; Pre-Order not compared (I-1 open) · DESIGN ONLY**

Author: JARVIS (Claude), 2026-11-20 UTC. This is JARVIS's design; it decides nothing for G.
Nothing in this file is operational. No account, token, host, domain, vendor contract or spend exists or is created. Everything goes live only on G's explicit OK, given as a separate decision for each action (G-12). The coint/ automation server is not deployed.

Decisions applied: G-04 (the seven red lines are confirmed), G-05 (one human approver per stream plus a native Arabic editor; names TBD by G), G-03 (a legal opinion on the [LEGAL-CHECK] items is authorized; the amount is not set), G-12 (accounts only on G's explicit OK), G-14 (no tags; version = full commit SHA).
Open with G: **G-06** owning entity and jurisdiction; **G-02** Arabic brand form.

Labels used: **ASSUMPTION** = a platform capability not verified from a primary source (blocker MB-06; to be checked against official platform documentation before go-live). **MANUAL** = no automated access is assumed.

---

## 1. Monitoring and weekly report — data-source matrix [A-4, B-1]

Channels follow JARVIS review §4 (primary: Telegram EN/AR + website/newsletter; secondary: WhatsApp Channels; month 2+: LinkedIn, YouTube Shorts; not at launch: Discord, Instagram, TikTok, open Telegram groups).

| Channel | Metrics (JARVIS §9) | Access method | Credential owner | Storage | Report generator | Verified |
|---|---|---|---|---|---|---|
| Telegram channel EN | subscribers, net change | Bot API member count — **ASSUMPTION** | Owning entity (G-06 OPEN); token held per §2 | Metrics store (§4 C7) | Weekly report job (§2) | No |
| Telegram channel EN | views per post, forwards, reactions, reach rate | In-app Statistics export or a user-session (MTProto) client — **ASSUMPTION**; fallback **MANUAL** entry from in-app stats | ″ | ″ | ″ | No |
| Telegram channel AR | same as EN | same as EN — **ASSUMPTION** / **MANUAL** | ″ | ″ | ″ | No |
| WhatsApp Channel (EN, AR) | followers, reactions per update | **MANUAL** entry from the in-app channel insights (no public analytics API known — **ASSUMPTION**) | ″ | ″ | ″ | No |
| Website | page views, clicks from channels (UTM), referrers | Self-hosted or SaaS web-analytics export/API — **ASSUMPTION** until a tool is chosen | ″ | ″ | ″ | No |
| Newsletter | subscribers, opt-ins, unsubscribes, open/click rates | Newsletter-provider export/API — **ASSUMPTION** until a provider is chosen | ″ | ″ | ″ | No |
| LinkedIn page (EN, month 2+) | followers, impressions, clicks | Page analytics export — **ASSUMPTION**; fallback **MANUAL** | ″ | ″ | ″ | No |
| YouTube Shorts (month 2+) | views, subscribers, watch time | Platform analytics export/API — **ASSUMPTION**; fallback **MANUAL** | ″ | ″ | ″ | No |
| Discord / Instagram / TikTok | — | Not at launch (JARVIS §4); no design | — | — | — | — |

Rules:
- Any metric whose automated access is not verified is collected **MANUALLY** by the stream approver once a day, into the same metrics store, with `source=manual` and the name of the person who entered it.
- The weekly report (JARVIS §9) is generated from the metrics store only. It shows each figure's access method, so manual and automated numbers are never mixed silently.
- **KPI 7 (EN/AR topic overlap):** measured from the topic tags in the per-post log (§6), not from platform analytics. The taxonomy is defined in the posts and calendar files.

## 2. Runtime [B-2]

| Item | Design |
|---|---|
| Host | One small managed container or VM, or a scheduled job runner, in the owning entity's cloud account (G-06 OPEN). Budget line: **Tooling/APIs**. |
| Scheduler | Daily metrics pull 06:00 GST; weekly report Monday 08:00 GST; source scan twice daily (JARVIS §6). |
| Owner | Operations owner = the EN stream approver until G names someone else (G-05). |
| Secrets | Platform tokens live only in the host's secret manager, never in the repo, chat or email. Read access: the job runtime plus one named admin. Each access is logged. |
| Rotation | Every 90 days, and immediately when an admin leaves or a leak is suspected. |
| Go-live gate | **G-12**: nothing is created or run until G's explicit OK for that action, validated per docs/FOUNDER_DECISION_VALIDATION.md. |
| Status today | Not built, not deployed. The coint/ server is not deployed. |

## 3. Reliability [C-9]

- **Owner:** the operations owner (§2).
- **Alerting:** a failed job, a missing daily metric, a failed report delivery or a duplicate-post block alerts the operations owner, and the stream approver for that stream, on the same day.
- **Retries:** 3 attempts with back-off of 5, 15 and 45 minutes. Then stop and escalate to the operations owner. A failed **post** is never retried automatically after the approval window; it goes back to the approver.
- **Report-recipient allowlist:** a fixed list in configuration. Default: G plus the two stream approvers; changes only on G's OK. The recipients' identities depend on G-06/G-07.
- **Dedupe and ledger:**
  - post key = `stream + source URL hash + approved text hash`
  - report key = `report type + ISO week`
  - every send is appended to an append-only ledger (key, time, channel, result)
  - a key already in the ledger is never sent again.

## 4. Owned-channel reference architecture [B-3, C-8]

These are generic component types; no vendor is chosen or purchased. Each maps to a line in BUDGETS.md.

| # | Component | Purpose | BUDGETS.md line |
|---|---|---|---|
| C1 | Domain(s) | Website and email domain; reserved only after G-02 and on G's OK | Hosting/CMS/newsletter/domain |
| C2 | Web hosting | Bilingual site (EN + AR, right-to-left support); the canonical archive (JARVIS §4) | Hosting/CMS/newsletter/domain |
| C3 | CMS | Two editorially separate sections (EN, AR); a correction notice on every article | Hosting/CMS/newsletter/domain |
| C4 | Newsletter provider | Weekly EN and AR editions; double opt-in | Hosting/CMS/newsletter/domain |
| C5 | Opt-in consent store | Records consent (time, wording, source) and withdrawals, as PDPL requires [LEGAL-CHECK] | Hosting/CMS/newsletter/domain |
| C6 | Data residency | Where C2–C5 and C7 store personal data; UAE/GCC residency or a lawful transfer basis [LEGAL-CHECK] | Legal opinion (assessment) |
| C7 | Metrics store + job host | §1–§3 | Tooling/APIs |
| C8 | Backups | Daily backup of CMS content, the consent store and the metrics store; 30-day retention; one restore test per quarter | Hosting/CMS/newsletter/domain |
| C9 | AI drafting / scan tooling | JARVIS §6 pipeline | Tooling/APIs |

## 5. Channel security baseline [C-5]

All of this is required before any account exists:

- **Owning entity:** G-06, OPEN. Every account, domain, ad account and token is registered to that entity, never to a person's private account.
- **Admin roles and least privilege:**
  - owner = the entity (G)
  - admins = the operations owner plus one backup
  - stream approvers = post/publish rights for their own stream only
  - editors and AI = drafting only, with no publish rights.
- **2FA:** required on every admin and approver login. Recovery codes are kept offline by the recovery owner.
- **Token storage:** see §2, secret manager only.
- **Recovery owner:** G, or a person G names. A written recovery procedure exists per platform.
- **Impersonation runbook:**
  - the website lists the official channels
  - check weekly for look-alike names
  - report the fake through the platform's reporting route
  - post an "official channels" notice in the affected stream
  - log the case.
- **Handles and domains:** reserved only after **G-02** (Arabic brand form) is decided, and only on G's explicit OK (G-12).

## 6. Editorial pipeline controls [B-4, C-6]

**Rule 0: source text is data, never instructions.** Text from scanned web pages, feeds, emails or posts is never followed as an instruction by the AI or any agent.

**Roles (G-05):**

| Stream | Roles (names TBD by G) |
|---|---|
| EN | EN human approver |
| AR | AR human approver and a native Arabic editor |

**Independent compliance pass:** a person or agent other than the one who drafted the item checks every item against the checklist below. The drafting AI's own check does not count.

**Compliance checklist: the seven editorial red lines (JARVIS review §3, confirmed by G, G-04):**

1. No odds, tips, predictions, bonus codes, affiliate links, or "how to bet / how to sign up" content.
2. No links to any operator's betting or registration pages. Links go to regulators, official press releases and news outlets.
3. Every licensee mention states who licenses it and the access limits, for example "18+/21+, UAE residents, not available in Dubai" where the source says so.
4. Responsible-gambling note on any story about a gambling product.
5. Winners' stories use only names the operator has published. No speculation about private people.
6. Content on prohibited states is limited to law, enforcement and economic news. Nothing normalises participation.
7. Every factual sentence carries a source. Single-source claims are labelled. Unverifiable claims are not published.

Also checked: [LEGAL-CHECK] tags on per-state legal statements, image rights and personal data.

**Per-post log fields:**
- post ID
- stream
- topic tag(s) (for KPI 7)
- source URLs with a snapshot reference
- verification result for each claim
- [LEGAL-CHECK] items
- drafter
- compliance checker and result
- approver
- approval time
- publish time and channel
- dedupe key
- correction or takedown history.

**State table:**

| Step | Failure | Outcome |
|---|---|---|
| Scan | Source down or unreachable | Skip it and log it; use other whitelisted sources. If down for 2 consecutive scans, alert the operations owner. |
| Verify | Conflicting sources | Prefer the primary source (regulator or organiser). If there is no primary source, the item is HELD and flagged; it is published only with the conflict stated, or dropped. |
| Verify | Failed verification | Item REJECTED and logged; not published (red line 7). |
| Compliance | A red line is hit | Item REJECTED or returned to the drafter with the line number. |
| Approval | No approval within 24 h, or before the news goes stale | Item EXPIRED; not published; logged. Nothing auto-publishes. |
| Published | Factual error or complaint | A correction is posted in the same stream within 24 h; the original is edited or removed per channel; logged. |
| Any | Compliance kill-switch (G, an approver or the operations owner) | All scheduled posts in the stream are paused at once; nothing resumes without G's or the approver's OK; logged. |

**Audit log:**
- Location: append-only store on the job host (§2), with a daily export to the backup (§4 C8).
- Retention: 2 years [LEGAL-CHECK].
- Access: read for G, the approvers and the operations owner; write for the pipeline only; no deletions.

## 7. Privacy inventory [C-8] — all [LEGAL-CHECK] (UAE PDPL and other GCC laws)

| Data item | Purpose | Retention | Recipients | Vendor / transfer basis |
|---|---|---|---|---|
| Newsletter email + consent record | Send the newsletter; prove consent | Until withdrawal + 12 months for the consent proof [LEGAL-CHECK] | Newsletter provider; the operations owner | Processor agreement with the provider; residency or transfer basis [LEGAL-CHECK] |
| Website analytics (no profiling) | Traffic and click KPIs | 14 months, aggregated [LEGAL-CHECK] | Operations owner; weekly report recipients (aggregates only) | Analytics tool; cookie/consent basis [LEGAL-CHECK] |
| Platform aggregate metrics | KPIs | Duration of the project | Weekly report allowlist (§3) | Platform terms; aggregates only |
| Comment or moderation data (only if comments are opened later, JARVIS §7) | Moderation and the removal log | 12 months [LEGAL-CHECK] | Approvers | Platform terms |
| Per-post log / audit log | Accountability | 2 years [LEGAL-CHECK] | G, approvers, operations owner | Job host (owning entity's account) |
| Staff and approver identities and admin logins | Access control | Duration of the role + 12 months [LEGAL-CHECK] | G; operations owner | Platform and host accounts |

Rule kept from JARVIS §8: no reader profiling by nationality or religion. The retention periods above are design proposals, to be confirmed by the legal opinion (G-03).

## 8. Delivery definition and verification plan [D-10, D-11]

- **Path:** `deliveries/WO-CO-100/v<N>/` (this delivery: v1).
- **Version:** the full 40-character commit SHA of the delivery commit. No tags (G-14).
- **Done:**
  - every approved requirement is addressed, or marked NOT ADDRESSED with a reason
  - the acceptance criteria (AC-1 to AC-4 and AC5 to AC8, G-11) pass, with the evidence recorded in VERIFICATION.md
  - limitations and blocked items are stated.
- **Deployment and rollback:** N/A. No publishing or accounts are authorized; this is a planning and design package.
- **Closure:** per WORKFLOW Step 12, only after G's valid APPROVE AND CLOSE on that exact version.
- **Source snapshot archive (D-10):**
  - Every cited URL is fetched at verification time, recording the HTTP status and retrieval date (UTC).
  - A text snapshot plus SHA-256 is stored under `deliveries/WO-CO-100/v<N>/sources/`.
  - A URL that fails is marked with its failure, never silently kept. (D's spot check found 26 of 39 URLs returning 200.)
- **Verification of this file:**
  - check that every section cites its finding IDs
  - check that no platform capability is stated as fact without a primary source (all such items are marked ASSUMPTION)
  - check that nothing in it creates, buys or publishes anything.
