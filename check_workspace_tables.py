import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename LIKE 'workspace_%'
        ORDER BY tablename;
    """)
    workspace_tables = cursor.fetchall()

    if workspace_tables:
        print(f"Found {len(workspace_tables)} workspace tables:")
        for table in workspace_tables:
            print(f"  - {table[0]}")
    else:
        print("No workspace tables found - cleanup successful!")

    # Also check for any tables with 'workspace' in the name
    cursor.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename LIKE '%workspace%'
        ORDER BY tablename;
    """)
    all_workspace_related = cursor.fetchall()

    if all_workspace_related:
        print(f"\nFound {len(all_workspace_related)} tables with 'workspace' in name:")
        for table in all_workspace_related:
            print(f"  - {table[0]}")