import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

print("=" * 80)
print("PRODUCTION DEPLOYMENT SCRIPT")
print("MIGRATING DATA FROM WORKSPACE TO CHAT TABLES")
print("=" * 80)

with connection.cursor() as cursor:
    # Check current state
    cursor.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename LIKE 'workspace_%'
        ORDER BY tablename;
    """)
    workspace_tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\nFound {len(workspace_tables)} workspace tables:")
    for table in workspace_tables:
        print(f"  - {table}")
    
    if not workspace_tables:
        print("\nNo workspace tables found. Skipping migration.")
    else:
        # Migrate chat messages if table exists
        if 'workspace_chatmessage' in workspace_tables:
            cursor.execute("SELECT COUNT(*) FROM workspace_chatmessage;")
            old_chat_count = cursor.fetchone()[0]
            print(f"\nworkspace_chatmessage has {old_chat_count} rows")
            
            if old_chat_count > 0:
                cursor.execute("""
                    INSERT INTO chat_chatmessage 
                    (id, sender_id, receiver_id, body, timestamp, is_deleted, attachment, is_read, is_edited)
                    SELECT id, sender_id, receiver_id, body, timestamp, is_deleted, attachment, is_read, is_edited
                    FROM workspace_chatmessage
                    ON CONFLICT (id) DO NOTHING;
                """)
                print(f"Migrated {cursor.rowcount} chat messages to chat_chatmessage")
        
        # Migrate company messages if table exists
        if 'workspace_companymessagetoadmin' in workspace_tables:
            cursor.execute("SELECT COUNT(*) FROM workspace_companymessagetoadmin;")
            old_company_count = cursor.fetchone()[0]
            print(f"\nworkspace_companymessagetoadmin has {old_company_count} rows")
            
            if old_company_count > 0:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'workspace_companymessagetoadmin'
                    ORDER BY ordinal_position;
                """)
                columns = [row[0] for row in cursor.fetchall()]
                print(f"Columns: {columns}")
                
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'chat_companymessagetoadmin'
                    ORDER BY ordinal_position;
                """)
                chat_columns = [row[0] for row in cursor.fetchall()]
                print(f"Chat columns: {chat_columns}")
        
        print("\n" + "=" * 80)
        print("DROPPING WORKSPACE TABLES")
        print("=" * 80)
        
        # Drop all workspace tables
        for table in workspace_tables:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                print(f"Dropped table: {table}")
            except Exception as e:
                print(f"Error dropping {table}: {e}")
        
        print("\n" + "=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        
        # Verify no workspace tables remain
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename LIKE 'workspace_%'
            ORDER BY tablename;
        """)
        remaining_tables = cursor.fetchall()
        
        if remaining_tables:
            print(f"\nWARNING: {len(remaining_tables)} workspace tables still exist:")
            for table in remaining_tables:
                print(f"  - {table[0]}")
        else:
            print("\nAll workspace tables successfully removed")
        
        # Check chat tables
        cursor.execute("SELECT COUNT(*) FROM chat_chatmessage;")
        chat_count = cursor.fetchone()[0]
        print(f"\nchat_chatmessage now has {chat_count} rows")

print("\n" + "=" * 80)
print("PRODUCTION DEPLOYMENT COMPLETE")
print("=" * 80)
print("\nNext steps:")
print("1. Run: python manage.py migrate")
print("2. Run: python manage.py collectstatic")
print("3. Restart your application server")
print("4. Clear cache if needed")
