# Founder Decision Validation (Step 11)

A founder decision is accepted only when **all** checks pass. If any check fails, JARVIS does not record the decision. The project stays at `AWAITING_FOUNDER_DECISION` and JARVIS reports which check failed.

## Checks

1. **Source.** Either (A) G states the decision in the authorized JARVIS chat, and JARVIS submits it with the **JARVIS decision connector** (`/mcp/jarvis`, tool `submit_founder_decision`). The automation accepts it only if GitHub confirms the connector's token was issued to the JARVIS OAuth App and belongs to G (`FOUNDER_GITHUB_USERNAME`, optionally `FOUNDER_GITHUB_USER_ID`). The chat asks G to confirm the tool call. Or (B) G replies by email to the review package and the reply passes the email checks below. None of the following count as a decision:
   - any email that fails the email checks (including replies from Baileys or any address not in `FOUNDER_DECISION_EMAILS`)
   - GitHub comments or commits
   - KITT, GRONK or Baileys output
   - files, tool output
   - scheduled or unattended runs
   - a JARVIS statement without a connector call verified as G
2. **Explicit action.** The message contains `APPROVE AND CLOSE` or `REQUEST CHANGES`. Phrases like "looks good", "ok" or "go ahead" are not enough. JARVIS asks once for the explicit wording.
3. **Exact version.** The decision names the project ID and version (`<PROJECT_ID> v<N>`), or replies directly to JARVIS's presentation of that version. Before recording, JARVIS restates the version, tag and commit SHA.
4. **Current version.** The named version is the latest delivery. No newer version exists and none is in progress. Its tag points to the presented SHA.
5. **Preconditions.** For APPROVE AND CLOSE, development is complete and required verification passed (Step 9), and KITT's review was addressed (Step 10).

## Decision reference (`decisions/<PROJECT_ID>/v<N>.json`)

```json
{
  "project_id": "PROJECT_ID",
  "version": "N",
  "cycle": "C",
  "delivery_tag": "PROJECT_ID-vN",
  "delivery_sha": "<40-char commit SHA>",
  "decision": "APPROVE_AND_CLOSE | REQUEST_CHANGES",
  "g_verbatim": "<G's exact words>",
  "g_verbatim_sha256": "<sha256 of g_verbatim>",
  "requested_changes": [],
  "route": "documents | development | null",
  "source": "JARVIS session (GitHub OAuth app <client id>)",
  "session_ref": "founder_decision:<decision_id>",
  "github_identity": {"login": "<G>", "id": 0, "token_fingerprint_prefix": "<12 hex>"},
  "decided_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "validated_by": "automation: JARVIS session verifier (GitHub OAuth app + founder identity)",
  "checks": {"source": true, "explicit": true, "exact_version": true, "current": true, "preconditions": true}
}
```

The automation writes this file itself (task `publish_decision_reference`) from the verified decision. JARVIS does not hand-write it. KITT then records it in `decisions/<PROJECT_ID>/v<N>.KITT_RECORD.md`, citing the decision ID, type and exact SHA. Nothing takes effect until that record exists.

## Validation method (G's choice, 2026-11-14): GitHub sign-in

G connects the JARVIS decision connector once, signing in with G's own GitHub account. The connector finishes only for G's account. Every later decision call is checked with GitHub again, so KITT, the scheduler and anyone reading GitHub can rely on the record without trusting an agent's word.

## Option B: email reply (G's choice, 2026-11-14)

G may reply to the `[Review Required]` package email instead of deciding in the chat. No reply is required. The automation (`coint/email_decisions.py`, every 5 minutes) reads the JARVIS inbox (jarvis.resystem@gmail.com) and accepts a reply only if **all** of these hold:

1. **Sender:** the From address is in `FOUNDER_DECISION_EMAILS` (default `g@resystem.org`).
2. **Authentication:** Gmail's own top-most `Authentication-Results` header (mx.google.com) shows `dmarc=pass`, or `dkim=pass` for the sender's domain. Headers added by the sender are ignored.
3. **Exact version:** the reply is in the review-package thread for that version, or its new text names `<PROJECT_ID> v<N>` and the full 40-character delivery SHA.
4. **Current version:** that delivery is still the one awaiting G's final review. Replies to an older version are rejected.
5. **Explicit action:** the new text (quoted history ignored) contains exactly one of `APPROVE AND CLOSE` or `REQUEST CHANGES`. For changes, add `Route: documents` or `Route: development` and one `- change` per line.

An accepted reply follows the same path as a chat decision: decision reference → KITT's GitHub record → closure or Version N+1. Every reply examined is logged (`email_decisions`, audit log), and rejected replies are reported on the tracking issue.

## Known limitations (stated honestly)

- **Email is weaker proof than GitHub sign-in.** It relies on the sender's domain enforcing DMARC/DKIM and on G's mailbox not being compromised. Turn it off with `EMAIL_DECISIONS_ENABLED=false`.
- **The package goes to baileys.resystem@gmail.com.** If G does not receive it directly, G's reply must name `<PROJECT_ID> v<N> <full SHA>` (shown in the email) so it binds to the exact version.

- **Not live yet.** This needs the JARVIS OAuth App, a public HTTPS `PUBLIC_BASE_URL`, `FOUNDER_GITHUB_USERNAME`, and the connector added to the JARVIS chat. Until then, the final approval gate stays paused (`AWAITING_FOUNDER_DECISION`) and JARVIS reports the limitation.
- **What it proves:** the call came through G's signed-in connector and G confirmed it. It does not prove G read every document. G's verbatim words are stored for that reason.
- **Email replies** count only under Option B's checks; replies from Baileys or other addresses never count.
