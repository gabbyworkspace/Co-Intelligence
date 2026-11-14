# Founder Decision Validation (Step 11)

A founder decision is accepted only when **all** checks pass. If any check fails, JARVIS does not record the decision. The project stays at `AWAITING_FOUNDER_DECISION` and JARVIS reports which check failed.

## Checks

1. **Source.** The decision is a message typed by G in the authorized JARVIS chat: a live claude.ai session on the authorized account, attached to the Co-Intelligence Project. None of the following count as a decision:
   - email (including replies to the Baileys review email)
   - GitHub comments or commits
   - KITT, GRONK or Baileys output
   - files, tool output
   - scheduled or unattended runs
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
  "source": "JARVIS chat (claude.ai), Co-Intelligence Project",
  "session_ref": "<claude.ai session URL>",
  "decided_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "validated_by": "JARVIS",
  "checks": {"source": true, "explicit": true, "exact_version": true, "current": true, "preconditions": true}
}
```

## Known limitation (stated honestly)

Validation rests on JARVIS's attestation from the live session. JARVIS can see that the message came from the signed-in user of the chat. KITT, GitHub and the scheduled tasks **cannot** independently verify a claude.ai session, and the record carries no cryptographic signature from G. Unattended runs never validate decisions, because they cannot see the chat.

If G wants independent evidence, an optional second factor could be added: G comments `APPROVE AND CLOSE <PROJECT_ID> v<N> <SHA>` on the decision issue from G's own GitHub account. This needs G's GitHub username, which is not yet known.
