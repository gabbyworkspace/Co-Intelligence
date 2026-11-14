# Architecture

```
GitHub ──webhook──▶ server.py ── verify_webhook ─▶ webhook_deliveries (durable) ─▶ 202
                                                       │
                       worker thread (woken at once) ◀─┘
                         process_delivery → handle_comment → parse_command → authorize_action
                         → command handler (one SQLite transaction: state + tasks + outbox)
                         → run_task: claim_task (lease) → load_manifest(exact SHA) → run_agent
                           → validate_output → checkpoint → publish_output (commit) → complete_and_route
                         → dispatch_outbox (GitHub comments / issue close)

KITT session (ChatGPT)  ─▶ /kitt/founder-decision   ─┐  SessionVerifier: token issued to THIS session's
JARVIS session (chat)   ─▶ /jarvis/founder-decision ─┘  OAuth App? user == founder? decision type allowed
   ─▶ founder_decisions + audit ─▶ command handlers. JARVIS-session decisions take effect only after
   KITT's record_founder_decision task publishes a GitHub record citing the validated decision.
   GitHub comments and agent statements can never perform founder actions.

scheduler.py (single process): recover_pending_tasks · monitor_overdue_tasks ·
                               email_recovery (process_email_outbox) · founder_reminders
```

## Stages (workflow) vs task states (execution)

| # | Stage | Role / task_type | Next |
|---|---|---|---|
| 1 | — (G ⇄ KITT in ChatGPT) | — | `project_start` decision with confirmed brief via KITT session |
| 2 | KITT_DRAFT | KITT `create_document` | FOUNDER_INITIAL_REVIEW |
| 3 | FOUNDER_INITIAL_REVIEW | FOUNDER gate (WAITING_FOUNDER) | approve → 4 · changes → 2 (rev+1) |
| 4 | KITT_APPLY_DECISIONS | KITT `apply_decisions` | 5 |
| 5 | JARVIS_DOC_REVIEW | JARVIS `doc_review` | 6 |
| 6 | KITT_FINALIZE | KITT `finalize_documents` | 7 |
| 7 | JARVIS_COUNCIL_PACKAGE | JARVIS `freeze_council_package` | frozen → 8 · not addressed → 6 (max 3 loops, then FOUNDER_DECISION) |
| 8 | COUNCIL_REVIEW | GRONK `council_dispatch` → COUNCIL_1..4 `council_review` | all four valid for same package → 9 |
| 9–10 | GRONK_DRAFT | GRONK `council_draft` | 11 |
| 10a | JARVIS_DEVELOPMENT | JARVIS `develop_and_deliver` (reconcile, develop, verify) | submitted → 10b · needs G → FOUNDER_DECISION |
| 10b | KITT_DELIVERY_REVIEW | KITT `delivery_review` | 10c |
| 10c | JARVIS_FINALIZE_DELIVERY | JARVIS `finalize_delivery` (addresses KITT findings) | submitted → 11 |
| 11 | FOUNDER_FINAL_REVIEW | FOUNDER gate, G ↔ JARVIS session; review package email → baileys.resystem@gmail.com | validated decision → recording |
| 11r | FOUNDER_DECISION_RECORDING | KITT `record_founder_decision` (GitHub record) | changes → Version N+1 · approve-close → CLOSED |
| 12 | CLOSED | — | final report email → g@resystem.org (outbox) |

Task states: QUEUED, RUNNING, WAITING_FOUNDER, BLOCKED, COMPLETED, FAILED,
CANCELLED, SUPERSEDED.

## Guarantees

- **Idempotency**: webhook `delivery_id` dedupe; comment-ID dedupe across webhook
  and recovery scan; tasks unique on `project|cycle|stage|role|input_sha|rev`.
- **Exclusive execution**: `UPDATE … WHERE state='QUEUED'` under `BEGIN IMMEDIATE`;
  leases with 60 s heartbeats; only leases expired beyond the grace period recover.
- **Exact versions**: every task carries an input commit SHA and per-file SHAs;
  outputs must echo the input SHA; council reviews must name the package SHA.
- **Checkpoints**: model output saved before publishing; published SHA saved
  before routing; retries resume from the last checkpoint.
- **Routing is code**: models choose only a verdict from `models.ROUTES`.
- **Founder authority**: only decisions verified from the authorized KITT session; email additionally requires the approval to reference an accepted `delivery_approve_close` founder decision for the same SHA.
- **Closure email**: six preconditions plus a JARVIS-session-validated approval and KITT's GitHub record of it, durable outbox, fixed Message-ID,
  SENDING → SENT | SEND_UNCERTAIN (reconcile) | PENDING (definite pre-send failure).
