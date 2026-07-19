# CoreLink Legacy Profile Cleanup - cPanel Deployment Guide

## Overview
This guide provides step-by-step instructions for deploying and executing the legacy profile cleanup script on cPanel production environment.

## Prerequisites
- SSH access to cPanel server
- Django project deployed on cPanel
- Python environment configured
- Database access credentials

## Step 1: Deploy the Cleanup Script

### 1.1 Upload the Script to Production
```bash
# From your local machine, navigate to project directory
cd C:\Users\city\corelink

# Upload the cleanup script to cPanel using SCP
scp profiles/management/commands/cleanup_legacy_profiles.py youruser@yourserver.com:/path/to/project/profiles/management/commands/
```

### 1.2 Verify File Permissions
```bash
# SSH into your cPanel server
ssh youruser@yourserver.com

# Navigate to your project directory
cd /path/to/project

# Verify the script exists
ls -la profiles/management/commands/cleanup_legacy_profiles.py

# Ensure it has proper permissions (644)
chmod 644 profiles/management/commands/cleanup_legacy_profiles.py
```

## Step 2: Run Dry-Run Test on Production

### 2.1 Activate Virtual Environment
```bash
# Navigate to your project directory
cd /path/to/project

# Activate your virtual environment
source venv/bin/activate  # or source venv/bin/activate.csh
```

### 2.2 Run Dry-Run Test
```bash
# Run the script in dry-run mode first
python manage.py cleanup_legacy_profiles --dry-run
```

### 2.3 Review Dry-Run Output
The dry-run will show:
- Migration verification status
- Legacy table counts
- Files that will be deleted
- Tables that will be dropped

**IMPORTANT:** Ensure migration verification shows **PASSED** before proceeding.

## Step 3: Execute Live Cleanup

### 3.1 Backup Database (CRITICAL)
```bash
# Create a database backup before running the cleanup
# Replace with your actual database credentials
mysqldump -u your_db_user -p your_db_name > backup_before_cleanup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup was created
ls -lh backup_before_cleanup_*.sql
```

### 3.2 Run Live Cleanup
```bash
# Execute the actual cleanup with --force flag
python manage.py cleanup_legacy_profiles --force
```

### 3.3 Monitor Execution
The script will:
1. Verify migration completeness
2. Analyze legacy tables
3. Drop 17 legacy database tables
4. Update profiles/models/__init__.py
5. Delete 7 legacy files
6. Generate final report

## Step 4: Post-Cleanup Verification

### 4.1 Verify Database State
```bash
# Check that legacy tables are gone
python manage.py dbshell

# In MySQL shell, run:
SHOW TABLES LIKE 'profiles_%';
# You should NOT see:
# - profiles_expertprofile
# - profiles_visionaryprofile
# - profiles_founderprofile
# - profiles_expertheadline
# - profiles_expertskill
# - profiles_expertcredential
# - profiles_expertproject
# - profiles_projectgalleryimage
# - profiles_expertexperience
# - profiles_jobpreference
# - profiles_expertthought
# - profiles_certification
# - profiles_project
# - profiles_projectimage
# - profiles_growthlog
# - profiles_learningtarget
# - profiles_visionblock

# Exit MySQL shell
exit
```

### 4.2 Verify File Deletion
```bash
# Verify legacy model files are deleted
ls profiles/models/expert.py  # Should return "No such file or directory"
ls profiles/models/visionary.py  # Should return "No such file or directory"
ls profiles/models/founder.py  # Should return "No such file or directory"

# Verify legacy command files are deleted
ls profiles/management/commands/migrate_to_unified_profiles.py  # Should return error
ls profiles/management/commands/migrate_right_now.py  # Should return error
ls profiles/management/commands/fix_legacy_founders.py  # Should return error
ls profiles/management/commands/fix_timestamps.py  # Should return error
```

### 4.3 Verify Application Still Works
```bash
# Test Django management commands
python manage.py check

# Test that the app loads without errors
python manage.py shell -c "from profiles.models import UserProfile; print('OK')"

# Test admin interface
python manage.py createsuperuser --noinput --username testuser --email test@test.com
```

### 4.4 Test User Registration
```bash
# Test that new user registration still works with unified models
python manage.py shell -c "
from accounts.models import CustomUser
from profiles.models.new_unified_profile import UserProfile
user = CustomUser.objects.create_user(username='testuser', email='test@test.com', password='testpass123')
profile = UserProfile.objects.create(user=user)
print('User and profile created successfully')
"
```

## Step 5: Cleanup Script Removal (Optional)

### 5.1 Remove Cleanup Script
```bash
# After successful cleanup, you can remove the cleanup script
rm profiles/management/commands/cleanup_legacy_profiles.py
```

## Troubleshooting

### Issue: Permission Denied
```bash
# Fix file permissions
chmod 644 profiles/management/commands/cleanup_legacy_profiles.py
```

### Issue: Import Error
```bash
# Ensure you're in the correct directory
cd /path/to/project
source venv/bin/activate
python manage.py cleanup_legacy_profiles --dry-run
```

### Issue: Database Connection Error
```bash
# Check your DATABASE settings in config/settings.py
# Ensure database credentials are correct for production
python manage.py dbshell
```

### Issue: Migration Verification Failed
```bash
# This means some users still have legacy profiles without UserProfile
# Run the migration command again
python manage.py migrate_to_unified_profiles
# Then retry cleanup
python manage.py cleanup_legacy_profiles --dry-run
```

## Rollback Procedure (If Needed)

### If Something Goes Wrong
```bash
# 1. Restore database from backup
mysql -u your_db_user -p your_db_name < backup_before_cleanup_YYYYMMDD_HHMMSS.sql

# 2. Restore deleted files from local backup
# You'll need to re-upload the deleted files from your local machine
scp profiles/models/expert.py youruser@yourserver.com:/path/to/project/profiles/models/
scp profiles/models/visionary.py youruser@yourserver.com:/path/to/project/profiles/models/
scp profiles/models/founder.py youruser@yourserver.com:/path/to/project/profiles/models/
# etc. for other files

# 3. Restore profiles/models/__init__.py
# Re-upload the original __init__.py from your local machine
```

## Summary of Changes

### Database Tables Deleted (17 total)
**Expert Tables (9):**
- profiles_expertprofile
- profiles_expertheadline
- profiles_expertskill
- profiles_expertcredential
- profiles_expertproject
- profiles_projectgalleryimage
- profiles_expertexperience
- profiles_jobpreference
- profiles_expertthought

**Visionary Tables (7):**
- profiles_visionaryprofile
- profiles_certification
- profiles_project
- profiles_projectimage
- profiles_growthlog
- profiles_learningtarget
- profiles_visionblock

**Founder Tables (1):**
- profiles_founderprofile

### Files Deleted (7 total)
**Model Files (3):**
- profiles/models/expert.py
- profiles/models/visionary.py
- profiles/models/founder.py

**Command Files (4):**
- profiles/management/commands/migrate_to_unified_profiles.py
- profiles/management/commands/migrate_right_now.py
- profiles/management/commands/fix_legacy_founders.py
- profiles/management/commands/fix_timestamps.py

### Files Modified (1 total)
- profiles/models/__init__.py (legacy imports removed)

## Final State Verification

After successful cleanup, your system will have:
- **Company** model and related tables
- **UserProfile** model and related tables
- No legacy ExpertProfile, VisionaryProfile, or FounderProfile models
- All user data preserved in unified UserProfile system

## Support

If you encounter any issues during deployment:
1. Check the error messages carefully
2. Review the troubleshooting section above
3. Ensure you have a recent database backup
4. Contact technical support if needed

## Safety Checklist

Before running live cleanup:
- [ ] Dry-run test completed successfully
- [ ] Migration verification shows PASSED
- [ ] Database backup created and verified
- [ ] Application is in maintenance mode (optional but recommended)
- [ ] You have SSH access to the server
- [ ] You know how to rollback if needed
- [ ] Team members are notified of the maintenance window
