# NetworkPost Table Cleanup Guide

## Overview
This guide explains how to safely remove the NetworkPost table from your database on both local and cPanel (production) environments.

## ⚠️ IMPORTANT WARNINGS
- **BACKUP YOUR DATABASE** before proceeding
- This action is **PERMANENT** and cannot be undone
- All NetworkPost data will be lost
- Test on local environment first before production

---

## LOCAL ENVIRONMENT CLEANUP

### Step 1: Backup Your Database
```bash
# If using SQLite
cp db.sqlite3 db.sqlite3.backup

# If using PostgreSQL
pg_dump corelink_db > corelink_backup.sql

# If using MySQL
mysqldump corelink_db > corelink_backup.sql
```

### Step 2: Run the Cleanup Script
```bash
python drop_networkpost_table.py
```

### Step 3: Apply Django Migrations
```bash
python manage.py migrate network 0008_drop_networkpost
```

### Step 4: Verify Cleanup
```bash
python manage.py shell
>>> from network.models import NetworkPost
>>> # This should raise an error if model doesn't exist
```

### Step 5: Restart Development Server
```bash
python manage.py runserver
```

---

## CPANEL (PRODUCTION) CLEANUP

### Step 1: Backup Your Database via cPanel

**For MySQL/MariaDB:**
1. Login to cPanel
2. Go to "phpMyAdmin"
3. Select your database
4. Click "Export" tab
5. Choose "Quick" export method
6. Click "Go" to download backup

**For PostgreSQL:**
1. Login to cPanel
2. Go to "phpPgAdmin"
3. Select your database
4. Click "Export"
5. Download the backup file

### Step 2: Upload Files to Production

Upload these files to your cPanel file manager:
- `drop_networkpost_table.py`
- Updated `network/models.py`
- Updated `network/views.py`
- Updated `network/urls.py`
- Updated `network/forms.py`
- Updated `network/migrations/0008_drop_networkpost.py`

### Step 3: Run Cleanup Script via SSH

**Connect to your cPanel via SSH:**
```bash
ssh yourusername@yourdomain.com
```

**Navigate to your project directory:**
```bash
cd public_html/corelink  # or your project path
```

**Activate virtual environment:**
```bash
source venv/bin/activate  # or source bin/activate
```

**Run the cleanup script:**
```bash
python drop_networkpost_table.py
```

### Step 4: Apply Migrations via SSH
```bash
python manage.py migrate network 0008_drop_networkpost
```

### Step 5: Restart Application

**For Python Applications:**
```bash
# Restart your Python app via cPanel
# Go to Setup Python App > Restart
```

**For Django with Passenger:**
```bash
touch tmp/restart.txt
```

---

## ALTERNATIVE: Manual SQL Cleanup (If Script Fails)

### For SQLite
```sql
DROP TABLE IF EXISTS network_networkpost;
```

### For PostgreSQL
```sql
DROP TABLE IF EXISTS network_networkpost CASCADE;
```

### For MySQL/MariaDB
```sql
DROP TABLE IF EXISTS network_networkpost;
```

---

## FILES THAT WERE REMOVED

### Python Files
- `network/models.py` - NetworkPost model removed
- `network/views.py` - NetworkPost views removed (nexus_posts, NetworkPostDetailView, MyNetworkPostListView, NetworkPostCreateView, NetworkPostUpdateView, NetworkPostDeleteView)
- `network/forms.py` - NetworkPostForm removed
- `network/urls.py` - NetworkPost URL patterns removed

### Template Files
- `theme/templates/network/my_signals.html`
- `theme/templates/network/nexus_posts.html`
- `theme/templates/network/signal_confirm_delete.html`
- `theme/templates/network/signal_detail.html`
- `theme/templates/network/signal_form.html`

### Migration Files
- All NetworkPost-related migrations will be cleaned up by the script

---

## VERIFICATION CHECKLIST

After cleanup, verify:

- [ ] NetworkPost model no longer exists in `network/models.py`
- [ ] NetworkPost views removed from `network/views.py`
- [ ] NetworkPost URLs removed from `network/urls.py`
- [ ] NetworkPostForm removed from `network/forms.py`
- [ ] Template files deleted
- [ ] Database table dropped
- [ ] Application runs without errors
- [ ] No references to NetworkPost in other apps

---

## ROLLBACK PLAN (If Something Goes Wrong)

### Restore Database from Backup

**For SQLite:**
```bash
cp db.sqlite3.backup db.sqlite3
```

**For PostgreSQL:**
```bash
psql corelink_db < corelink_backup.sql
```

**For MySQL:**
```bash
mysql corelink_db < corelink_backup.sql
```

### Restore Code Files
Restore the original files from your version control (Git) or backup.

---

## TROUBLESHOOTING

### Error: "Table doesn't exist"
- This is normal if the table was already removed
- Continue with migration steps

### Error: "Migration dependency not found"
- Delete all migration files in `network/migrations/` except `__init__.py`
- Run: `python manage.py makemigrations network`
- Run: `python manage.py migrate network`

### Error: "Foreign key constraint fails"
- This means other tables reference NetworkPost
- You may need to drop those tables first or remove foreign key constraints

---

## POST-CLEANUP TASKS

1. **Update navigation menus** - Remove links to NetworkPost pages
2. **Update user documentation** - Remove references to NetworkPost features
3. **Check for hardcoded URLs** - Search codebase for `/nexus/signals/`, `/broadcast/`, etc.
4. **Test application thoroughly** - Ensure no broken links or errors

---

## CONTACT SUPPORT

If you encounter issues:
1. Check Django logs: `python manage.py check`
2. Review error messages carefully
3. Restore from backup if needed
4. Contact your hosting provider for cPanel-specific issues
