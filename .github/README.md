# recall-ai / AskMyVideo CI/CD

GitHub Actions pipeline for the Django video search app, deployed to mitch-cloud VPS following the same pattern as [wnba-stat-spot](https://github.com/mitchelldawkinsjr/wnba-stat-spot).

## Workflows

| Workflow | File | Triggers | Purpose |
|----------|------|----------|---------|
| CI Pipeline | `ci.yml` | push/PR to `main`, `develop` | Django tests, lint, Docker build verify |
| Deploy to VPS | `deploy-vps.yml` | push to `main` (path-filtered), manual | rsync → build → migrate → health check |
| Security Scan | `security.yml` | push/PR, weekly Mon 3am UTC | pip-audit, bandit, secrets guard |
| VPS Health Check | `health-check.yml` | every 30 min, manual | SSH curl to `localhost:8030/health/` |

## Required repository secrets

These must match the secrets used by wnba-stat-spot (same VPS):

| Secret | Description |
|--------|-------------|
| `VPS_HOST` | VPS IP or hostname |
| `VPS_USER` | SSH user (e.g. `root` or `deploy`) |
| `VPS_SSH_KEY` | Private key for SSH/rsync deploy |

## Optional secrets

| Secret | Description |
|--------|-------------|
| `SLACK_WEBHOOK` | Slack notifications on deploy success/failure and health alerts |

## VPS layout

```
/opt/360ws/clients/docker-app/recall-ai/
├── .env                          # production secrets (never in git)
├── docker-compose.prod.yml
├── Dockerfile.prod
└── deploy/env.production.example
```

- **Host port:** `8030` → container `8000`
- **NPM proxy target:** `http://recall-ai-app:8000` on `360ws-network`
- **Health:** `GET /health/` and `GET /api/health/`

## Manual deploy

```bash
gh workflow run deploy-vps.yml
```

## Local CI parity

```bash
pip install -r requirements-ci.txt
DJANGO_SETTINGS_MODULE=video_recall_project.settings SECRET_KEY=test python manage.py test video_processor
```
