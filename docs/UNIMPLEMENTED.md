# Unimplemented integrations and known limitations

Status: **code complete and tested against in-memory fakes. NOT deployed, NOT live.**
Nothing here has been run against the real GitHub App, the JARVIS Gmail account,
or any model provider.

## Missing before go-live (configuration, not code)

| Item | State | What is needed |
|---|---|---|
| `FOUNDER_GITHUB_USERNAME` | not set | G's actual GitHub login. Service refuses to start without it. |
| **KITT session OAuth App + GPT Action** | **not created — BLOCKER for brief and initial review** | GitHub OAuth App, KITT GPT Action importing `/kitt/openapi.json`, G signs in once (OPERATING.md §5). |
| **JARVIS chat connector** | **built, not connected — BLOCKER for final approval** | MCP connector at `/mcp/jarvis` with GitHub sign-in is implemented and tested against simulated GitHub. Still needed: JARVIS GitHub OAuth App, public HTTPS `PUBLIC_BASE_URL`, adding the connector to the JARVIS chat, G signing in once. Not yet tried against the real Claude connector flow. |
| GitHub App | not created/installed | App ID, installation ID, private key, webhook secret, repo ID (see OPERATING.md §1) |
| JARVIS Gmail OAuth | not authorized here | OAuth client + refresh token for jarvis.resystem@gmail.com (scopes `gmail.send`, `gmail.readonly`) |
| KITT adapter | **unsupported** (default) | Choose `anthropic`, `openai_compat`, `http`, or `manual` |
| JARVIS adapter | **unsupported** (default) | same |
| GRONK adapter | **unsupported** (default) | e.g. `openai_compat` → `https://api.x.ai/v1` |
| COUNCIL_1..4 adapters | **unsupported** (default) | four separately configured callable reviewers |
| Public HTTPS endpoint | not provided | reverse proxy / load balancer in front of `:8080/webhook` |

`python -m coint doctor` reports every one of these and exits non-zero until fixed.

## Things the automation deliberately does not do

- **Ordinary chats cannot be invoked.** A claude.ai Project, ChatGPT or Grok web
  chat named KITT/JARVIS/GRONK has no callable API. Such a role must use an API
  adapter or `manual` (a person/agent publishes files and posts `/handoff`).
- **Native GRONK council** is not used; the four reviews are four separately
  tracked calls (`COUNCIL_1..4`). GRONK is invoked only to prepare the draft.
- **Code execution for JARVIS development.** Model adapters return file contents;
  they do not run code. Verification evidence is what JARVIS reports plus GitHub
  check runs on the delivery SHA (`REQUIRE_CHECKS_PASS=true`). Running real tests
  needs a CI workflow on `co-intel/*` branches or an `http` adapter pointing at a
  sandboxed coding agent. Neither is included.
- **Inbox delivery** is never claimed: only Gmail API acceptance (message ID +
  timestamp) is recorded.
- **Review package email** goes to baileys.resystem@gmail.com from the JARVIS
  Gmail account. Only Gmail API acceptance is recorded; inbox delivery is not
  confirmed.
- **Pending-review notifications** are GitHub comments mentioning the owning
  agent (KITT for initial review, JARVIS for final review) plus that session's
  `/pending` endpoint. Neither ChatGPT nor a Claude chat can receive pushed
  messages, so an agent sees new items when G opens the session (and the agent
  checks pending reviews) or via its GitHub @mention.
- **Email-reply decisions** (optional, final review only) read the JARVIS inbox
  every 5 minutes and need the Gmail OAuth `gmail.readonly` scope. They are only
  as strong as the sender domain's DMARC/DKIM and G's mailbox security.
- **KITT's own work from ChatGPT.** KITT's tasks (draft, apply decisions,
  finalize, delivery review, recording G's final decisions) still need files committed to GitHub and a `/handoff`
  from KITT's configured GitHub login (`ADAPTER_KITT_KIND=manual`). A ChatGPT GPT
  cannot do that unless it is given a GitHub-writing action; that action is
  **not implemented here**. Alternatively run KITT's drafting through an API
  adapter and keep ChatGPT only for G's conversation and decisions.
- **Residual trust in the sessions:** the server verifies the session's OAuth
  app and that the signed-in user is G; ChatGPT (and Claude connectors) ask G to
  confirm each decision call. It cannot prove that G read every word of the package; the
  verbatim `founder_statement` is recorded for that reason.
- **No founder mailbox polling or email approval parsing** exists (none was
  ever implemented). Gmail is used only to send JARVIS's final report and to
  search JARVIS's own sent mail when a send outcome is uncertain.
- **No auto-merge / PR creation.** Artifacts live on `co-intel/<PROJECT_ID>`;
  merging to `main` is left to G.
- **Text artifacts only.** `commit_files` writes UTF-8 text; binary assets must
  be committed by a `manual` role and referenced in a `/handoff`.

## Engineering limitations

- SQLite (WAL) on one host. For multiple hosts, port `db.py` to PostgreSQL with
  `SELECT … FOR UPDATE SKIP LOCKED` claims (schema is portable).
- Network calls happen inside some SQLite write transactions (command handling);
  fine at this volume, revisit if throughput grows.
- Cost limit is a pre-call worst-case estimate (chars/3.5 + max output tokens)
  and requires `ADAPTER_<ROLE>_PRICE_*` to be configured; otherwise doctor warns.
- Gmail reconciliation relies on `rfc822msgid:` search; a message not found
  within `EMAIL_RECONCILE_WAIT_MINUTES` is re-sent with the **same** Message-ID.
- GitHub Actions is not used (scheduler is a long-running process or system cron).
