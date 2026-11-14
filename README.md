# Co-Intelligence

Multi-agent delivery workflow: G (founder), KITT, JARVIS, GRONK (council), Baileys.

- [WORKFLOW.md](WORKFLOW.md) — full flow, v2.0 (Steps 10–12 updated 2026-11-14)
- [config/routing.yaml](config/routing.yaml) — states, owners, notifications, reminders
- [docs/FOUNDER_DECISION_VALIDATION.md](docs/FOUNDER_DECISION_VALIDATION.md) — how G's decision is validated
- [templates/](templates/) — review-package and closure emails

Folder layout per project:

```
deliveries/<PROJECT_ID>/v<N>/   delivery, VERIFICATION.md, FINDINGS.md, KITT_REVIEW.md
council/<PROJECT_ID>/           MANIFEST.json (frozen SHA), GRONK return
decisions/<PROJECT_ID>/v<N>.json   validated founder decision (+ KITT record)
closure/<PROJECT_ID>/CLOSURE.json
ledger/emails.jsonl             every email send result (dedupe)
```
