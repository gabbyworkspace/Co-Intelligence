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

## 5. Using it (G)

Open one GitHub issue per project and discuss freely — nothing runs until G
posts, as the **first line** of a new comment:

````
/project start
```json
{"title": "…", "objective": "…", "scope": ["…"], "deliverables": ["…"],
 "acceptance_criteria": ["…"], "constraints": ["…"], "confirmed": true,
 "project_id": "CI-0001"}
```
````

Then the automation posts **Review Required** comments containing the exact
commands to copy:

| Command | Who | Effect |
|---|---|---|
| `/initial approve <cycle> <document_sha>` (+ optional `{"decisions": […]}`) | G | KITT applies decisions → JARVIS |
| `/initial changes <cycle> <document_sha>` + `{"changes": […]}` | G | KITT revises (same cycle, new revision) |
| `/handoff <role> <task_type> <cycle> <input_sha>` + manifest | assigned agent | completes a `manual` task |
| `/delivery changes <cycle> <delivery_sha>` + `{"changes": […], "route": "documents"\|"development"}` | G | starts Version N+1 |
| `/delivery approve-close <cycle> <delivery_sha>` | G | validates, records approval + closure, closes issue, then final email |
| `/project status` | G or agents | posts status table |
| `/project pause` / `/project resume` | G | stop/continue; `resume` + `{"decisions": […]}` answers an escalation |

SHAs must be full 40-character commit SHAs. Commands are parsed only from the
first line of a newly created comment; quoted text, code blocks, edits and bot
comments are never executed. Closing the issue by hand is **not** approval.

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

- **Task BLOCKED** (auth/permission/invalid input): fix the cause, then G posts
  `/project resume` (re-queues blocked tasks of the current cycle).
- **Task FAILED** after 1/5/15-minute retries: inspect `python -m coint audit
  --project <ID>`; G can `/project resume` after fixing.
- **Email BLOCKED**: read `email_outbox.last_error`; a precondition failed (it
  will never send until the cause is fixed and the row is set back to PENDING by
  an operator).
- **SEND_UNCERTAIN**: wait; the email job searches the mailbox for the fixed
  Message-ID before any resend.
- **Backups**: copy the SQLite file with `sqlite3 coint.sqlite3 ".backup b.db"`.
- **Audit**: every command, task transition, handoff, approval, closure and
  email attempt is in `audit_events` (actor, action, version, timestamp, outcome).
