# Operating instructions

## 1. GitHub App (prompt pickup + identity)

1. Create a GitHub App owned by `gabbyworkspace`.
   - Webhook URL: `https://<your-host>/webhook`, secret: a long random string.
   - Repository permissions: **Issues** read/write, **Contents** read/write,
     **Pull requests** read, **Checks** read, **Metadata** read.
   - Subscribe only to: **Issues**, **Issue comment**, **Pull request**,
     **Check run**, **Check suite**.
2. Install it on `gabbyworkspace/Co-Intelligence` only.
3. Put App ID, installation ID, repo ID, bot login (`<app-slug>[bot]`) in the
   environment; private key and webhook secret in your secret manager
   (`*_FILE` variables). Never commit them.

## 2. JARVIS Gmail

Create a Google Cloud OAuth client, authorize **jarvis.resystem@gmail.com**
once with scopes `https://www.googleapis.com/auth/gmail.send` and
`https://www.googleapis.com/auth/gmail.readonly`, and store the refresh token as
a secret. `coint doctor` confirms the authorized address; if it is not
`jarvis.resystem@gmail.com`, final emails are blocked.

## 3. Adapters

Set `ADAPTER_<ROLE>_KIND` for KITT, JARVIS, GRONK, COUNCIL_1..4:

| kind | use for | required |
|---|---|---|
| `anthropic` | Claude via API | `_MODEL`, key env (default `ANTHROPIC_API_KEY`), prices |
| `openai_compat` | OpenAI, xAI Grok, other compatible APIs | `_ENDPOINT` base URL, `_MODEL`, `_API_KEY_ENV`, prices |
| `http` | your own agent service | `_ENDPOINT` (receives `{role, task_type, system, user, limits}`) |
| `manual` | a person/agent working in GitHub | `_GITHUB_LOGIN` (only this login may `/handoff` that role) |

Role instructions: `prompts/*.md`; output contract: `prompts/OUTPUT_SCHEMA.md`.

## 4. Run

```bash
cp .env.example .env            # fill in non-secret values; secrets via *_FILE
docker compose up -d --build    # web (webhook + worker) and scheduler
docker compose exec web python -m coint doctor
```
Without Docker: `pip install -r requirements.txt`, then run
`python -m coint serve` and **one** of `python -m coint scheduler` or the
crontab in `deploy/crontab.example` (systemd units in `deploy/systemd/`).

Run tests: `pip install -r requirements-dev.txt && pytest`.

## 5. Founder decisions — through the authorized KITT session only

G talks only to KITT in ChatGPT. There is no founder chatbot, founder email, or
founder GitHub command. Founder decisions reach the automation through one
trusted integration:

```
G ⇄ KITT (ChatGPT custom GPT) ──GPT Action, GitHub OAuth (G signs in)──▶ POST /kitt/founder-decision
                                                                      └▶ GET  /kitt/pending
```

**Setup**
1. Create a **GitHub OAuth App** dedicated to KITT's GPT Action (not the GitHub
   App from §1). Put its client ID/secret in `KITT_OAUTH_CLIENT_ID` /
   `KITT_OAUTH_CLIENT_SECRET_FILE`.
2. In the KITT GPT → *Actions* → import `https://<host>/kitt/openapi.json`.
   Authentication: OAuth · client ID/secret of that OAuth App · authorization URL
   `https://github.com/login/oauth/authorize` · token URL
   `https://github.com/login/oauth/access_token` · scope `read:user`.
   Copy the ChatGPT callback URL into the OAuth App's callback URL.
3. G uses the GPT and signs in with **G's own GitHub account** the first time.
4. Add `prompts/kitt.md` → "Founder relay" to the GPT instructions.

**What is validated on every decision** (`coint/kitt_session.py`)
- GitHub confirms the bearer token was issued to the KITT OAuth App
  (`POST /applications/{client_id}/token`) — i.e. it comes from the authorized
  KITT session — and that its user is `FOUNDER_GITHUB_USERNAME`
  (and `FOUNDER_GITHUB_USER_ID` if set). The token is never stored; only a
  SHA-256 fingerprint.
- The action is marked consequential, so ChatGPT shows G the exact payload and
  G must press **Confirm** before it is sent.
- The decision is bound to `project_id`, `cycle` and the exact 40-char `sha`
  G reviewed; stale versions, wrong stages and replays (`decision_id` reused
  with different content) are rejected.
- Every decision (accepted or rejected) is stored in `founder_decisions`,
  written to the audit log, and posted as a **Founder decision recorded**
  comment on the tracking issue.

**Decision types**

| decision_type | Required fields | Effect |
|---|---|---|
| `project_start` | `brief` (title, objective, scope, deliverables, acceptance_criteria, constraints, `confirmed: true`), optional `issue_number` | creates tracking issue if needed, commits `brief/confirmed-brief.json`, starts KITT |
| `initial_approve` | `project_id`, `cycle`, `sha` (+ optional `decisions`) | KITT applies decisions → JARVIS |
| `initial_changes` | + `changes` | KITT revises (same cycle) |
| `delivery_changes` | + `changes`, `route` (`documents`/`development`) | Version N+1 |
| `delivery_approve_close` | `project_id`, `cycle`, `sha` | validates delivery, records approval + closure, closes issue → final email |
| `project_pause` / `project_resume` | `project_id` (+ `decisions` when answering an escalation) | |

All require `decision_id` (new UUID) and `founder_statement` (G's words, verbatim).

**Founder review packages** are posted on the tracking issue as
"📨 Review Required — founder review package for KITT to present to G"
(mentioning KITT's GitHub login) and served with document contents at the exact
version by `GET /kitt/pending` (`listPendingFounderReviews`). Daily reminders
(09:17 Dubai) mention KITT. Nothing advances on a reminder.

**Never approval evidence:** any GitHub comment (KITT's or anyone's, including
G's own account), an issue close, a label, or an agent's claim. Such comments
are rejected with an explanation.

**If the integration is unavailable** (not configured, OAuth app credentials
rejected), `/kitt/founder-decision` returns **503 with a `blocker`** and
`coint doctor` reports it. There is no bypass.

`/project status` remains available as a GitHub comment for G and the agents.

## 6. Handoff manifest (manual roles)

````
/handoff JARVIS apply_decisions 1 <commit_sha>
```json
{"project_id": "CI-0001", "task_id": "T-…", "revision": 1, "source_role": "KITT",
 "files": ["documents/project-document.md", "approvals/initial-decisions.md"],
 "expected_outputs": ["reviews/jarvis/doc-review.md"],
 "next_action": "JARVIS reviews the document", "verdict": "done"}
```
````
Files must already be committed at `<commit_sha>` (any branch, merged or not)
under `projects/<PROJECT_ID>/`.

## 7. Schedules (UTC)

| Job | Cron | Purpose |
|---|---|---|
| recover_pending_tasks | `*/5 * * * *` | unprocessed webhooks, missed comments/handoffs, expired leases, eligible tasks |
| monitor_overdue_tasks | `2,17,32,47 * * * *` | stalled tasks, missing council reviews (60 min default) |
| email_recovery | `*/5 * * * *` | approved+closed cycles without a confirmed final email; uncertain-send reconciliation |
| founder_reminders | `17 5 * * *` | 09:17 Asia/Dubai; once per 24 h per pending review; never advances work |

## 8. Runbook

- **Task BLOCKED** (auth/permission/invalid input): fix the cause, then G tells KITT to resume
  (`project_resume` decision; re-queues blocked tasks of the current cycle).
- **Task FAILED** after 1/5/15-minute retries: inspect `python -m coint audit
  --project <ID>`; G can resume via KITT after fixing.
- **Email BLOCKED**: read `email_outbox.last_error`; a precondition failed (it
  will never send until the cause is fixed and the row is set back to PENDING by
  an operator).
- **SEND_UNCERTAIN**: wait; the email job searches the mailbox for the fixed
  Message-ID before any resend.
- **Backups**: copy the SQLite file with `sqlite3 coint.sqlite3 ".backup b.db"`.
- **Audit**: every command, task transition, handoff, approval, closure and
  email attempt is in `audit_events` (actor, action, version, timestamp, outcome).
