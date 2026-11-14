# Co-Intelligence

Multi-agent delivery workflow: G (founder), KITT, JARVIS, GRONK (council), Baileys.

## Workflow (v2.0)

- [WORKFLOW.md](WORKFLOW.md) — full flow, v2.0 (Steps 10–12 updated 2026-11-14)
- [config/routing.yaml](config/routing.yaml) — states, owners, notifications, reminders
- [docs/FOUNDER_DECISION_VALIDATION.md](docs/FOUNDER_DECISION_VALIDATION.md) — how G's decision is validated
- [templates/](templates/) — review-package and closure emails

Folder layout per project (workflow documents):

```
deliveries/<PROJECT_ID>/v<N>/   delivery, VERIFICATION.md, FINDINGS.md, KITT_REVIEW.md
council/<PROJECT_ID>/           MANIFEST.json (frozen SHA), GRONK return
decisions/<PROJECT_ID>/v<N>.json   validated founder decision (+ KITT record)
closure/<PROJECT_ID>/CLOSURE.json
ledger/emails.jsonl             every email send result (dedupe)
```

## Automation engine (`coint/`)

Automation for the same workflow: G → KITT → JARVIS → GRONK + four council
reviewers → JARVIS → KITT → JARVIS → G. G's decisions are accepted only from
validated sessions (initial review: KITT in ChatGPT; final review: JARVIS chat)
and recorded on GitHub by KITT. It has a durable task queue, a single scheduler,
review packages to baileys.resystem@gmail.com, and a post-closure report from
jarvis.resystem@gmail.com to g@resystem.org.

> **Status: implemented and tested locally; not deployed and not live.**
> See [docs/UNIMPLEMENTED.md](docs/UNIMPLEMENTED.md) for what must be configured.
>
> **Layout not yet aligned:** the engine writes artifacts to
> `projects/<PROJECT_ID>/{brief,documents,assets,reviews,council,development,verification,delivery,approvals}`
> on branch `co-intel/<PROJECT_ID>` and keeps its email ledger in its database.
> The workflow documents above use `deliveries/`, `decisions/`, `closure/` and
> `ledger/emails.jsonl`. One layout must be adopted before projects such as
> FLOW-TEST-001 can run through the engine.

- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Operating instructions and commands: [docs/OPERATING.md](docs/OPERATING.md)
- Agent prompts and output contract: [prompts/](prompts/)
- Environment template (no secrets): [.env.example](.env.example)

```bash
pip install -r requirements-dev.txt
pytest                                   # 64 tests incl. the 14 acceptance tests
FOUNDER_GITHUB_USERNAME=<g-login> python -m coint doctor
docker compose up -d --build
```
