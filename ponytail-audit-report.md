# Ponytail Audit Report — video-processor-mvp

**Date:** 2026-06-16  
**Mode:** `/ponytail-audit` (whole-repo, one-shot, no fixes applied)  
**Scope:** `video-processor-mvp/` (excludes `venv/`, `node_modules/`)

---

## Ranked findings (biggest cut first)

| # | Tag | Path | Finding |
|---|-----|------|---------|
| 1 | `delete:` | `a11y-audit/report-*.json`, `summary-*.json` | ~18,700 lines of generated axe output committed; belongs in CI artifacts |
| 2 | `delete:` | `AWS_DEPLOYMENT_*.md`, `DEPLOYMENT_*.md`, `PRODUCTION_*.md`, etc. | ~6,500 lines overlapping deployment/status docs |
| 3 | `shrink:` | `video_processor/views.py` | 2,241-line god module — 4 search APIs, duplicate converters, teams stubs |
| 4 | `delete:` | `semantic_search.py`, `enhanced_semantic_search.py`, `ai_enhanced_search.py`, `rag_qa_system.py` | Four parallel search stacks (~2,350 lines), duplicate FAISS init |
| 5 | `delete:` | `task-definition-*.json` (9 files) | Iterative ECS debug snapshots; many reference legacy `settings_dev` |
| 6 | `delete:` | `Dockerfile`, `Dockerfile.simple`, `Dockerfile.minimal`, `Dockerfile.prod.fixed` | Five Dockerfiles; keep one prod canonical |
| 7 | `delete:` | `deploy-*.sh`, `startup*.sh`, `aws-setup.sh`, etc. | ~1,800 lines overlapping deploy/startup scripts |
| 8 | `yagni:` | `celery.py`, django-celery-beat/results, redis in compose | Celery wired but no `tasks.py`, no `@shared_task`, sync processing in views |
| 9 | `yagni:` | `djangorestframework`, `drf-spectacular` | APIs are `@csrf_exempt` JsonResponse views, not DRF |
| 10 | `delete:` | `enhanced_whisper_pipeline.py` | 501 lines imported at startup, never called; core uses `core_video_processor.py` |
| 11 | `delete:` | `video_recall_project/settings_dev.py` | Legacy settings superseded by `settings/__init__.py` |
| 12 | `delete:` | `youtube_downloader.py` | Standalone CLI duplicating `yt_dlp` in views; never imported |
| 13 | `delete:` | `templates/.../navigation.html` | 192 lines, zero references in repo |
| 14 | `yagni:` | Teams API endpoints in `views.py` | Hard-coded fake data, no Teams model |
| 15 | `shrink:` | `includes/library_scripts.html` | 1,330 lines with runtime DOM injection for hybrid-batch UI |
| 16 | `delete:` | `management/migrations/0001_initial.py` | Orphan migration in wrong directory |
| 17 | `stdlib:` | `core_requirements.txt` → `ffmpeg-python` | Never imported; ffmpeg via `subprocess` everywhere |
| 18 | `yagni:` | `datasets`, `accelerate`, `scikit-learn` | Zero Python imports; keyword search is plain string match |
| 19 | `shrink:` | `whisper_compat.py` | 127-line shim mostly for unused `enhanced_whisper_pipeline.py` |
| 20 | `delete:` | `check_db.py`, `diagnose_user_stats.py`, `test_core_processor.py` | Ad-hoc root scripts outside Django test suite |

---

## net: ~6,500–7,500 lines, -6 to -10 deps possible

*(application code + deploy config only)*

**Including docs + a11y artifacts:** ~32,000 lines removable

---

## Dependency cuts (core_requirements.txt)

| Remove | Tag | Why |
|--------|-----|-----|
| `ffmpeg-python` | stdlib: | Use subprocess (already done) |
| `datasets`, `accelerate`, `scikit-learn` | yagni: | Never imported |
| `celery`, beat, results | yagni: | No task modules |
| `redis`, `django-redis` | yagni: | Unused in app code |
| `djangorestframework`, `drf-spectacular` | yagni: | JsonResponse views only |
| `opencv-python` → headless | shrink: | CI already uses headless |

**Keep:** Django, gunicorn, whitenoise, psycopg2, yt-dlp, faster-whisper, torch, transformers, sentence-transformers, faiss-cpu, numpy, Pillow, boto3 (prod).

---

## Ponytail boundaries (not flagged)

- Accessibility fixes on `fix/a11y-wcag-audit` — correct, not bloat
- Security/correctness bugs — separate review pass
- Stitch design tokens — intentional product requirement
