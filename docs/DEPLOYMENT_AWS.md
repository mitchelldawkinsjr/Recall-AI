# AWS / ECS deployment (dormant)

**Status:** DORMANT — VPS Docker is the active production target. These assets are preserved for a future AWS migration if user demand requires scale-out.

## When to revive

- Traffic exceeds single-VPS capacity
- Need managed RDS/ECS autoscaling
- S3-backed media at scale

Before reactivating, open a dedicated issue to validate terraform state, task definitions, and `Dockerfile.prod` against current app code.

## Artifacts in this repo

| Path | Purpose |
|------|---------|
| `terraform/` | ECS/RDS infrastructure definitions |
| `scripts/setup-*.sh` | AWS resource bootstrap scripts |
| `scripts/migrate-sqlite-to-postgres.py` | One-time DB migration helper |
| `deploy-aws.sh` | AWS deploy entrypoint (if present) |
| `deploy-production.sh` | Legacy production deploy (if present) |
| `startup-aws.sh` | ECS/RDS-oriented startup (see below) |

## Environment

Production settings support optional S3 storage when `USE_S3=True`:

- `boto3`, `django-storages` in `core_requirements.txt`
- S3 block in `video_recall_project/settings/production.py`

## VPS vs AWS

| | VPS (active) | AWS (dormant) |
|--|--------------|---------------|
| Deploy workflow | `.github/workflows/deploy-vps.yml` | None in CI |
| Compose | `docker-compose.prod.yml` | ECS task definitions in `terraform/` |
| Docs | `docs/DEPLOYMENT.md` | This file |

## Related

- Active deploy: [deploy/vps-deploy.sh](../deploy/vps-deploy.sh)
- Env template: [deploy/env.production.example](../deploy/env.production.example)
