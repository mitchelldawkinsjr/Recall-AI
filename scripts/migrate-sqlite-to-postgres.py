#!/usr/bin/env python
"""
SQLite to PostgreSQL Migration Script
Migrates data from SQLite database to PostgreSQL
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'video_recall_project.settings')
django.setup()

from django.db import connections
from django.core.management import call_command
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import json
from datetime import datetime


def get_sqlite_connection(db_path):
    """Get SQLite connection"""
    return sqlite3.connect(db_path)


def get_postgres_connection(database_url):
    """Get PostgreSQL connection from DATABASE_URL"""
    import dj_database_url
    db_config = dj_database_url.parse(database_url)
    
    return psycopg2.connect(
        host=db_config['HOST'],
        port=db_config['PORT'],
        database=db_config['NAME'],
        user=db_config['USER'],
        password=db_config['PASSWORD']
    )


def migrate_table(sqlite_conn, pg_conn, table_name, columns, skip_if_empty=False):
    """Migrate a single table from SQLite to PostgreSQL"""
    print(f"📦 Migrating table: {table_name}")
    
    # Read from SQLite
    cursor_sqlite = sqlite_conn.cursor()
    cursor_sqlite.execute(f"SELECT * FROM {table_name}")
    rows = cursor_sqlite.fetchall()
    
    if skip_if_empty and len(rows) == 0:
        print(f"   ⏭️  Skipping empty table")
        return
    
    print(f"   Found {len(rows)} rows")
    
    if len(rows) == 0:
        return
    
    # Write to PostgreSQL
    cursor_pg = pg_conn.cursor()
    
    # Build column names
    col_names = [col[0] for col in cursor_sqlite.description]
    placeholders = ','.join(['%s'] * len(col_names))
    col_names_str = ','.join([f'"{col}"' for col in col_names])
    
    # Clear existing data (if any)
    cursor_pg.execute(f'TRUNCATE TABLE "{table_name}" CASCADE')
    
    # Insert data
    try:
        execute_values(
            cursor_pg,
            f'INSERT INTO "{table_name}" ({col_names_str}) VALUES %s',
            rows,
            template=None,
            page_size=100
        )
        pg_conn.commit()
        print(f"   ✅ Migrated {len(rows)} rows")
    except Exception as e:
        pg_conn.rollback()
        print(f"   ❌ Error migrating {table_name}: {e}")
        raise


def main():
    """Main migration function"""
    print("🚀 Starting SQLite to PostgreSQL Migration")
    print("=" * 50)
    
    # Get database URLs
    sqlite_path = os.environ.get('SQLITE_DB_PATH', 'db.sqlite3')
    postgres_url = os.environ.get('DATABASE_URL')
    
    if not postgres_url:
        print("❌ Error: DATABASE_URL environment variable not set")
        print("   Example: postgresql://user:password@host:port/database")
        sys.exit(1)
    
    if not os.path.exists(sqlite_path):
        print(f"❌ Error: SQLite database not found: {sqlite_path}")
        sys.exit(1)
    
    print(f"📂 Source (SQLite): {sqlite_path}")
    print(f"📂 Target (PostgreSQL): {postgres_url.split('@')[1] if '@' in postgres_url else 'hidden'}")
    print()
    
    # Connect to databases
    print("🔌 Connecting to databases...")
    sqlite_conn = get_sqlite_connection(sqlite_path)
    pg_conn = get_postgres_connection(postgres_url)
    print("✅ Connected")
    print()
    
    # Run Django migrations on PostgreSQL first
    print("📊 Running Django migrations on PostgreSQL...")
    os.environ['DATABASE_URL'] = postgres_url
    try:
        call_command('migrate', verbosity=0, interactive=False)
        print("✅ Migrations completed")
    except Exception as e:
        print(f"⚠️  Migration warning: {e}")
    print()
    
    # Get list of tables from SQLite
    cursor_sqlite = sqlite_conn.cursor()
    cursor_sqlite.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor_sqlite.fetchall()]
    
    print(f"📋 Found {len(tables)} tables to migrate")
    print()
    
    # Migrate each table
    django_tables = [
        'django_migrations',
        'django_content_type',
        'auth_permission',
        'auth_group',
        'auth_group_permissions',
        'auth_user',
        'auth_user_groups',
        'auth_user_user_permissions',
        'django_admin_log',
        'django_session',
    ]
    
    app_tables = [t for t in tables if t not in django_tables]
    
    # Migrate Django tables first
    for table in django_tables:
        if table in tables:
            try:
                migrate_table(sqlite_conn, pg_conn, table, None, skip_if_empty=True)
            except Exception as e:
                print(f"   ⚠️  Warning: {e}")
    
    # Migrate application tables
    for table in app_tables:
        try:
            migrate_table(sqlite_conn, pg_conn, table, None)
        except Exception as e:
            print(f"   ⚠️  Warning: {e}")
    
    # Close connections
    sqlite_conn.close()
    pg_conn.close()
    
    print()
    print("=" * 50)
    print("🎉 Migration completed!")
    print()
    print("📝 Next steps:")
    print("   1. Verify data in PostgreSQL database")
    print("   2. Update DATABASE_URL in your application configuration")
    print("   3. Test the application with PostgreSQL")
    print("   4. Keep SQLite backup until verified")


if __name__ == '__main__':
    main()

