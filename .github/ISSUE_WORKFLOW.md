# Issue workflow (AskMyVideo / recall-ai)

Automated issue → implement → review loop (mirrors fasted_calendar_pwa).

## Labels

| Label | Meaning |
|-------|---------|
| `needs-spec` | Triggers `issue-spec.yml` — GPT posts acceptance criteria |
| `spec-added` | Spec comment posted; required before implementation |
| `ready` | Triggers `issue-implement.yml` — Cursor cloud agent implements |
| `agent-working` | Agent running |
| `agent-failed` | Dispatch failed; fix and re-add `ready` |
| `pr-opened` | Implementation PR exists |
| `review-dispatched` | Bugbot + Ponytail dispatched |
| `review-running` | Reviews in progress |
| `review-clean` | No findings |
| `review-findings` | Findings on PR |

## Flow

1. Create issue → add `needs-spec`
2. Wait for spec comment → `spec-added` applied automatically
3. Add `ready` → cloud agent opens **draft** PR with `Fixes #N`
4. On PR open → `pr-review.yml` runs Bugbot + Ponytail in parallel
5. On success → PR marked ready; issue gets `review-clean` or `review-findings`
6. Merge → `deploy-vps.yml` deploys to mitch-cloud (if VPS secrets set)

## Required GitHub secrets

- `CURSOR_API_KEY` — agent implement + PR review
- `OPENAI_API_KEY` — issue spec generation
- `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` — deploy + health check
- `SLACK_WEBHOOK` (optional)

## Manual retry

If review fails: remove `review-dispatched`, re-add `pr-opened` on the issue.
