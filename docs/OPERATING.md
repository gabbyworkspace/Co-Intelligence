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

## 5. Founder decisions — two validated sessions, KITT records everything

| Phase | G talks to | Decisions | Session endpoint |
|---|---|---|---|
| Initial brief and document review | KITT (ChatGPT) | `project_start`, `initial_approve`, `initial_changes` | `/kitt/*` |
| Final delivery review | JARVIS (JARVIS chat) | `delivery_approve_close` (APPROVE AND CLOSE), `delivery_changes` (REQUEST CHANGES) | `/jarvis/*` |
| Escalations | whoever owns the phase | `project_resume` (+ `decisions`) | either |
| Pause / resume | either | `project_pause`, `project_resume` | either |

Each session integration calls this service with a GitHub OAuth token from its
**own** OAuth App, obtained when G signs in with GitHub inside that session.
Every decision is accepted only if GitHub confirms the token was issued to that
session's app and belongs to `FOUNDER_GITHUB_USERNAME` (and
`FOUNDER_GITHUB_USER_ID` if set). A KITT-session token is refused on the JARVIS
endpoints and vice versa, and each session may only submit its own decision
types. Decisions are bound to `project_id`, `cycle` and the exact 40-character
`sha`; stale versions, wrong stages and replayed `decision_id`s are rejected.
Every decision (accepted or rejected) goes to `founder_decisions`, the audit log,
and a comment on the tracking issue. The token is never stored.

**Never approval evidence:** a GitHub comment (from KITT, JARVIS or G's own
account), an email reply, an issue close or label, or any agent statement.

### Final review flow (steps 10–12)

1. JARVIS completes development and verification → **KITT `delivery_review`**
   (via GitHub) → **JARVIS `finalize_delivery`** addresses every KITT finding.
2. The finalized version is tagged `<PROJECT_ID>-v<N>` and enters `FOUNDER_FINAL_REVIEW`: a "Review Required — for
   JARVIS to present to G" comment is posted, and the **review package is
   emailed from jarvis.resystem@gmail.com to baileys.resystem@gmail.com**
   (durable outbox; failures are posted on the issue). `/jarvis/pending` gives
   JARVIS the project ID, cycle, exact SHA, summary, verification, limitations,
   KITT's review and the email status, including the exact chat confirmation to
   use only after a successful send.
3. G decides in the JARVIS chat. The automation writes the validated decision
   reference `decisions/<PROJECT_ID>/v<N>.json` and hands it to **KITT
   `record_founder_decision`**, which publishes
   `decisions/<PROJECT_ID>/v<N>.KITT_RECORD.md` citing the decision reference. A record
   that does not cite the validated decision is refused.
4. Only after KITT's record: **APPROVE AND CLOSE** → approval re-validated
   against the exact current delivery, `closure/<PROJECT_ID>/CLOSURE.json`
   written, tag `<PROJECT_ID>-v<N>-closed`, tracking issue closed, final report
   emailed to g@resystem.org. Every send result is appended to
   `ledger/emails.jsonl` (and the final one to `CLOSURE.json`). **REQUEST CHANGES** → Version N+1
   (previous cycle preserved), routed to KITT (documents) or JARVIS
   (development), reviewed again, and back to G through JARVIS. No closure, no
   final report.

### Setup

- **KITT session**: GitHub OAuth App + KITT GPT Action importing
  `https://<host>/kitt/openapi.json` (OAuth: authorize
  `https://github.com/login/oauth/authorize`, token
  `https://github.com/login/oauth/access_token`, scope `read:user`).
- **JARVIS session (connector)**:
  1. Create a second GitHub OAuth App (the JARVIS app). Callback URL:
     `https://<host>/oauth/callback`. Put its ID/secret in
     `JARVIS_OAUTH_CLIENT_ID` / `JARVIS_OAUTH_CLIENT_SECRET_FILE`, and set
     `PUBLIC_BASE_URL=https://<host>`.
  2. In Claude, add a custom connector with URL `https://<host>/mcp/jarvis` and
     enable it in the Co-Intelligence project chat (the JARVIS chat). Claude
     discovers the OAuth settings automatically (`/.well-known/...`) and
     registers itself; only Claude's callback URLs are accepted.
  3. G connects it and signs in with **G's own GitHub account**. The connection
     is refused for any other GitHub user.
  4. Tools: `list_pending_final_reviews` (read-only) and
     `submit_founder_decision` (the chat asks G to confirm each call).
  The same decisions can also be sent to `/jarvis/founder-decision` with a token
  from the JARVIS OAuth App (spec at `/jarvis/openapi.json`).

**If a session integration is unavailable**, its endpoints return **503 with a
`blocker`**, `coint doctor` reports it, and the workflow waits at that gate.
There is no bypass.

`/project status` remains available as a GitHub comment for G and the agents.

### Repository layout (WORKFLOW.md v2.0)

Agents work with logical paths (`prompts/OUTPUT_SCHEMA.md`); `coint/layout.py`
maps them to the team layout: `<PROJECT_ID>/` (brief, documents, assets, doc
review), `council/<PROJECT_ID>/` (MANIFEST.json, reviews/, drafts/),
`deliveries/<PROJECT_ID>/v<N>/` (DELIVERY.md, FINAL-REPORT.md, VERIFICATION.md/
.json, KITT_REVIEW.md, FINDINGS.md/.json, IMPLEMENTATION.md, development/),
`decisions/`, `closure/`, `ledger/emails.jsonl`. Commits go to branch
`co-intel/<PROJECT_ID>`.

**Adopting a brief KITT already published** (e.g. FLOW-TEST-001): KITT submits
`project_start` with `project_id`, `title`, `issue_number`, `confirmed: true`
and `brief_ref: {"path": "FLOW-TEST-001/INITIAL-BRIEF-v1.0.md", "sha": "<commit>"}`
after G confirms it in the KITT session.

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
