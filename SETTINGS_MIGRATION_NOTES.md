# Settings Module Migration Notes

## Overview
The Django settings structure has been updated to use a proper package structure with `settings/` directory containing:
- `base.py` - Base settings shared by all environments
- `__init__.py` - Development settings (default)
- `production.py` - Production settings

## Changes Made

### Settings Structure
- **Old**: `video_recall_project/settings.py` (deleted)
- **Old**: `video_recall_project/settings_dev.py` (consolidated into `settings/__init__.py`)
- **New**: `video_recall_project/settings/` package structure

### Settings Module References
- **Development**: `video_recall_project.settings` (uses `__init__.py`)
- **Production**: `video_recall_project.settings.production`

### Updated Files
The following files have been updated to use the new settings structure:
- `startup-ec2.sh`
- `health-check.sh`
- `setup-ec2-env.sh`
- `deploy-ec2.sh`

### Files Still Using `settings_dev` (Need Manual Update)
The following files still reference `settings_dev` and should be updated when deploying:
- AWS ECS Task Definition JSON files (`task-definition*.json`)
- Some deployment scripts in `scripts/` directory

**Note**: These files are typically updated during deployment, so they can be updated when needed.

## Environment Variables

### Required for Production
- `SECRET_KEY` - Must be set (raises error if missing)
- `ALLOWED_HOSTS` - Must be set (raises error if missing)
- `DJANGO_SETTINGS_MODULE=video_recall_project.settings.production`

### Optional
- `DATABASE_URL` - For PostgreSQL (defaults to SQLite if not set)
- `REDIS_URL` - For Redis/Celery (defaults to dummy cache if not set)
- `DEBUG` - Defaults to False in production
- `CORS_ALLOWED_ORIGINS` - Comma-separated list of allowed origins

## Migration Steps

1. **Update Environment Variables**:
   ```bash
export DJANGO_SETTINGS_MODULE=video_recall_project.settings.production
   ```

2. **Set Required Variables**:
   ```bash
   export SECRET_KEY="your-secret-key-here"
   export ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com"
   ```

3. **Test Settings**:
   ```bash
   python manage.py check --settings=video_recall_project.settings.production
   ```

4. **Update Deployment Scripts**:
   - Update any deployment scripts that reference `settings_dev`
   - Update AWS ECS task definitions if using ECS

## Breaking Changes

1. **User Field Default Removed**: The `VideoJob.user` field no longer has `default=1`. All code that creates `VideoJob` instances must explicitly provide a user. This is already handled in the codebase.

2. **Settings Import**: If any code directly imports from `settings_dev`, it will need to be updated.

## Verification

To verify the settings are working correctly:

```bash
# Development
python manage.py check

# Production
python manage.py check --settings=video_recall_project.settings.production
```

## Rollback

If you need to rollback, you can:
1. Restore `settings_dev.py` from git history
2. Update `DJANGO_SETTINGS_MODULE` back to `video_recall_project.settings_dev`
3. Note: This is not recommended as the new structure is more maintainable

