# Agent output schema

Every adapter must return a single JSON object:

```json
{
  "verdict": "<one of the verdicts allowed for the task type>",
  "summary": "Short description of what was done",
  "files": { "documents/project-document.md": "...full file content..." },
  "blockers": ["unresolved issue needing G or another role"],
  "limitations": ["known limitation"],
  "next_action": "What the destination role must do next"
}
```

The automation adds cycle/revision/task/input-SHA metadata to every file it
publishes (an HTML comment header on Markdown, a `_coint` key on JSON).

## Allowed verdicts and required files per task type

| task_type | verdicts | required files |
|---|---|---|
| create_document | done | brief/brief.json, documents/project-document.md |
| apply_decisions | done | documents/project-document.md, approvals/initial-decisions.md |
| doc_review | accepted, changes_requested | reviews/jarvis/doc-review.md |
| finalize_documents | done | documents/project-document.md, documents/feedback-response.md |
| freeze_council_package | frozen, feedback_not_addressed | council/packages/manifest.json |
| council_review | done | council/reviews/<ROLE>.md (e.g. council/reviews/COUNCIL_2.md) |
| council_draft | done | council/drafts/proposed-final-draft.md, council/drafts/findings-index.json, council/drafts/conflict-decision-log.md, council/drafts/unresolved-blockers.md |
| develop_and_deliver | submitted, requires_founder_decision | reviews/jarvis/finding-dispositions.json, documents/implementation-document.md, verification/verification-report.json, delivery/delivery.md, delivery/final-report.md |
| delivery_review (KITT) | accepted, changes_requested | reviews/kitt/delivery-review.md, reviews/kitt/delivery-findings.json |
| finalize_delivery (JARVIS) | submitted, requires_founder_decision | everything develop_and_deliver requires + reviews/jarvis/kitt-findings-response.json |
| record_founder_decision (KITT) | recorded | approvals/founder-decision-<decision_id>.md citing the decision_id, decision_type and exact delivery SHA |

### reviews/kitt/delivery-findings.json

```json
{"findings": [{"id": "K-1", "severity": "high|medium|low", "requirement": "AC2",
  "summary": "...", "required_change": "..."}]}
```

### reviews/jarvis/kitt-findings-response.json

```json
{"responses": [{"finding_id": "K-1", "action": "fixed|clarified|rejected|requires_founder_decision",
  "details": "..."}]}
```
Every KITT finding must have a response.

### council/packages/manifest.json (freeze_council_package)

```json
{"includes": ["documents/project-document.md", "assets/..."],
 "approved_requirements": ["..."], "open_questions": ["..."],
 "acceptance_criteria": ["..."]}
```
Every path in `includes` must exist at the input version.

### council/drafts/findings-index.json

```json
{"findings": [{"id": "F-001", "reviewers": ["COUNCIL_1","COUNCIL_3"],
  "severity": "high|medium|low", "summary": "...", "proposed_resolution": "..."}]}
```

### reviews/jarvis/finding-dispositions.json

```json
{"dispositions": [{"finding_id": "F-001",
  "disposition": "accepted|rejected|resolved|requires_founder_decision",
  "reason": "required for rejected and requires_founder_decision"}]}
```
Every finding in the findings index must have exactly one disposition.

### verification/verification-report.json

```json
{"development_complete": true,
 "status": "passed|failed|partial",
 "checks": [{"name": "...", "acceptance_criterion": "...", "result": "passed|failed|not_run",
             "evidence": "command, output excerpt, or link"}],
 "limitations": ["..."], "unresolved_issues": ["..."]}
```
