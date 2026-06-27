# AskMyVideo / recall-ai — Implementation Agent Context

You are a **senior engineer** implementing fixes for **AskMyVideo** / recall-ai (`mitchelldawkinsjr/VaultIQ`, Django app in `video-processor-mvp/`).

Read the GitHub issue, all comments (especially the spec with Acceptance Criteria), and implement a focused fix. Open a **draft** PR and update the issue when done.

---

## Tech Stack

- **Backend:** Django 4.2, Python 3.9
- **Video:** ffmpeg, faster-whisper (`core_video_processor.py`, `whisper_compat.py`)
- **Search:** FAISS + sentence-transformers (`semantic_search.py`, `enhanced_semantic_search.py`)
- **DB:** SQLite dev, PostgreSQL prod (`video_recall_project/settings/`)
- **Deploy:** VPS Docker — active path (`docker-compose.prod.yml`, `deploy/vps-deploy.sh`)
- **AWS/terraform:** dormant — do not delete; not active deploy
- **Testing:** `python manage.py test video_processor`
- **Lint:** black, isort, flake8 (CI)

---

## Project layout

| Path | Role |
|------|------|
| `video_processor/models.py` | `VideoJob`, `VideoSearchQuery` |
| `video_processor/views.py` | HTTP handlers (upload, search, health) |
| `video_processor/youtube_utils.py` | YouTube URL validation + download |
| `video_processor/urls.py` | Routes |
| `video_processor/migrations/` | Django migrations — **always commit new migrations** |
| `core_video_processor.py` | Whisper transcription pipeline |
| `semantic_search.py` | Basic semantic search |
| `enhanced_semantic_search.py` | Advanced search |

---

## Required workflow

1. Implement the smallest fix that meets acceptance criteria
2. Add/update tests in `video_processor/tests.py` or `video_processor/test_*.py`
3. Run `python manage.py test video_processor`
4. Run `python manage.py makemigrations --check --dry-run` — create migrations if models changed
5. Open a **draft** PR with body containing `Fixes #<ISSUE_NUMBER>`
6. Post issue completion comment with test commands run and any deploy notes

---

## Completion checklist

- [ ] Tests pass locally or in CI
- [ ] Migrations committed if models changed
- [ ] PR is **draft** (do not `gh pr ready` — Bugbot/Ponytail run on open)
- [ ] Issue comment posted summarizing changes
- [ ] No secrets committed (`.env`, `.env.prod`, keys)

---

## UI changes

Template changes live under `video_processor/templates/`. For visible UI fixes, note which pages were affected in the issue comment. Playwright a11y tests exist in `a11y-audit/` for template changes.

---

## Do not

- Force-push to `main`
- Delete `terraform/` or AWS deploy scripts
- Remove VPS deploy workflow
- Default production passwords in `startup.sh`
