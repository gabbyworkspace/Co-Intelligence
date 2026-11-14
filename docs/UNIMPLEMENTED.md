# Unimplemented integrations and known limitations

Status: **code complete and tested against in-memory fakes. NOT deployed, NOT live.**
Nothing here has been run against the real GitHub App, the JARVIS Gmail account,
or any model provider.

## Missing before go-live (configuration, not code)

| Item | State | What is needed |
|---|---|---|
| `FOUNDER_GITHUB_USERNAME` | not set | G's actual GitHub login. Service refuses to start without it. |
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
- **Founder reminders** are GitHub @mentions only (no email, by spec default).
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
