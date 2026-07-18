"""
Production deployment script for content and subscriptions app removal.
Run this on cPanel production to:
1. Drop all content and subscriptions tables from database
2. Verify cleanup was successful
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def production_cleanup():
    """Drop all content and subscriptions tables on production."""
    
    print("=" * 60)
    print("PRODUCTION CLEANUP: Content & Subscriptions Apps")
    print("=" * 60)
    
    with connection.cursor() as cursor:
        # Check current state
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND (tablename LIKE 'content_%' OR tablename LIKE 'subscriptions_%')
            ORDER BY tablename;
        """)
        tables_to_drop = cursor.fetchall()
        
        if not tables_to_drop:
            print("No content or subscriptions tables found - already clean!")
            print("=" * 60)
            return
        
        print(f"\nFound {len(tables_to_drop)} tables to drop:")
        for table in tables_to_drop:
            print(f"  - {table[0]}")
        
        print("\nProceeding with table deletion...")
        
        # Drop each table
        dropped_count = 0
        for table in tables_to_drop:
            table_name = table[0]
            try:
                cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;')
                print(f"[OK] Dropped: {table_name}")
                dropped_count += 1
            except Exception as e:
                print(f"[ERROR] Error dropping {table_name}: {e}")
        
        # Verify cleanup
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND (tablename LIKE 'content_%' OR tablename LIKE 'subscriptions_%');
        """)
        remaining = cursor.fetchall()
        
        print("\n" + "=" * 60)
        print(f"SUMMARY: Dropped {dropped_count} tables")
        
        if remaining:
            print(f"[WARNING] {len(remaining)} tables still remain:")
            for table in remaining:
                print(f"  - {table[0]}")
        else:
            print("[SUCCESS] All content and subscriptions tables successfully dropped!")
        print("=" * 60)

if __name__ == "__main__":
    production_cleanup()
