# Co-Intelligence

Automation for the Co-Intelligence project workflow: G → KITT → JARVIS → GRONK +
four council reviewers → JARVIS → G, with G's decisions accepted only from the
authorized KITT ChatGPT session (OAuth-verified), GitHub issue records and agent handoffs, with a durable task queue, a single scheduler, and a post-closure
report sent from jarvis.resystem@gmail.com to g@resystem.org.

> **Status: implemented and tested locally; not deployed and not live.**
> See [docs/UNIMPLEMENTED.md](docs/UNIMPLEMENTED.md) for what must be configured.

- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Operating instructions and commands: [docs/OPERATING.md](docs/OPERATING.md)
- Agent prompts and output contract: [prompts/](prompts/)
- Environment template (no secrets): [.env.example](.env.example)

```bash
pip install -r requirements-dev.txt
pytest                                   # 56 tests incl. the 14 acceptance tests
FOUNDER_GITHUB_USERNAME=<g-login> python -m coint doctor
docker compose up -d --build
```

Project artifacts are written to `projects/<PROJECT_ID>/{brief,documents,assets,
reviews/jarvis,council/{packages,reviews,drafts},development,verification,
delivery,approvals}` on branch `co-intel/<PROJECT_ID>`.
