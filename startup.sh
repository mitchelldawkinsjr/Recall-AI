#!/bin/bash

# Enhanced Startup script for Video Processor MVP
# Designed for ECS Fargate with proper error handling and logging

set -euo pipefail

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S UTC')] $1" >&2
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S UTC')] ERROR: $1" >&2
}

# Pre-flight checks
log "🚀 Starting Video Processor MVP..."

# Check Python is available
if ! command -v python &> /dev/null; then
    log_error "Python not found in PATH"
    exit 1
fi

# Check Django is installed
if ! python -c "import django" 2>/dev/null; then
    log_error "Django not installed"
    exit 1
fi

# Check required directories exist
REQUIRED_DIRS=("/app" "/app/media" "/app/static" "/app/search_cache")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        log "Creating directory: $dir"
        mkdir -p "$dir" || {
            log_error "Failed to create directory: $dir"
            exit 1
        }
    fi
done

# Set environment variables if not set
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-video_recall_project.settings.production}"
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Wait for database to be ready (with retries) - only if DATABASE_URL is set (PostgreSQL/RDS)
if [ -n "${DATABASE_URL:-}" ]; then
    log "📊 Checking database connectivity (PostgreSQL/RDS)..."
    MAX_DB_RETRIES=30
    DB_RETRY_COUNT=0
    DB_READY=false
    
    while [ $DB_RETRY_COUNT -lt $MAX_DB_RETRIES ]; do
        if python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '$DJANGO_SETTINGS_MODULE')
django.setup()
from django.db import connection
connection.ensure_connection()
" 2>/dev/null; then
            log "✅ Database connection successful"
            DB_READY=true
            break
        else
            DB_RETRY_COUNT=$((DB_RETRY_COUNT + 1))
            log "⏳ Waiting for database... (attempt $DB_RETRY_COUNT/$MAX_DB_RETRIES)"
            sleep 2
        fi
    done
    
    if [ "$DB_READY" = false ]; then
        log_error "Database not ready after $MAX_DB_RETRIES attempts"
        exit 1
    fi
else
    log "📊 Using SQLite database (no DATABASE_URL set)"
    # SQLite doesn't need connection checks, just verify file can be created/accessed
    if python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '$DJANGO_SETTINGS_MODULE')
import django
django.setup()
from django.conf import settings
db_path = settings.DATABASES['default']['NAME']
print('SQLite database path:', db_path)
" 2>/dev/null; then
        log "✅ SQLite database configured"
    else
        log "⚠️  SQLite database check had warnings, continuing..."
    fi
fi

# Run database migrations (with retries)
log "📊 Running database migrations..."
MIGRATION_RETRIES=3
MIGRATION_SUCCESS=false

for i in $(seq 1 $MIGRATION_RETRIES); do
    if python manage.py migrate --noinput 2>&1; then
        log "✅ Migrations completed successfully"
        MIGRATION_SUCCESS=true
        break
    else
        log "⚠️  Migration attempt $i/$MIGRATION_RETRIES failed, retrying..."
        sleep 5
    fi
done

if [ "$MIGRATION_SUCCESS" = false ]; then
    log_error "Migrations failed after $MIGRATION_RETRIES attempts"
    # Continue anyway - migrations might already be applied
fi

# Collect static files (with retries)
log "📁 Collecting static files..."
STATIC_RETRIES=3
STATIC_SUCCESS=false

for i in $(seq 1 $STATIC_RETRIES); do
    if python manage.py collectstatic --noinput 2>&1; then
        log "✅ Static files collected successfully"
        STATIC_SUCCESS=true
        break
    else
        log "⚠️  Static collection attempt $i/$STATIC_RETRIES failed, retrying..."
        sleep 2
    fi
done

if [ "$STATIC_SUCCESS" = false ]; then
    log_error "Static file collection failed after $STATIC_RETRIES attempts"
    # Continue anyway - static files might already be collected
fi

# Create superuser if it doesn't exist (non-blocking)
log "👤 Checking superuser..."
python manage.py shell -c "
from django.contrib.auth.models import User
import os
if not User.objects.filter(username='admin').exists():
    try:
        User.objects.create_superuser(
            'admin',
            os.environ.get('ADMIN_EMAIL', 'admin@example.com'),
            os.environ.get('ADMIN_PASSWORD', 'admin123')
        )
        print('✅ Superuser created: admin')
    except Exception as e:
        print(f'⚠️  Superuser creation failed: {e}')
else:
    print('ℹ️  Superuser already exists')
" 2>&1 || log "⚠️  Superuser check failed, continuing..."

# Pre-warm application (load AI models in background if needed)
log "🔥 Pre-warming application..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '$DJANGO_SETTINGS_MODULE')
import django
django.setup()
# Import to trigger lazy loading of AI components
try:
    from video_processor.models import VideoJob
    print('✅ Django models loaded')
except Exception as e:
    print(f'⚠️  Model loading warning: {e}')
" 2>&1 || log "⚠️  Pre-warming had warnings, continuing..."

# Determine number of workers (default to 2, can be overridden)
WORKERS=${GUNICORN_WORKERS:-2}
TIMEOUT=${GUNICORN_TIMEOUT:-300}

log "🌐 Starting Gunicorn server with $WORKERS workers..."

# Start Gunicorn with proper error handling
exec gunicorn video_recall_project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "$WORKERS" \
    --timeout "$TIMEOUT" \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output \
    --enable-stdio-inheritance \
    --preload




