# Oracle Periodic Update - Cron Job Setup

## Overview
This guide sets up the Oracle rating system to automatically recalculate scores every 5 minutes using cron jobs.

## Prerequisites
- SSH access to HahuCloud server
- Django project deployed at `/home/corelink`
- Python virtual environment activated

## Cron Job Configuration

### Option 1: Add to User's Crontab (Recommended)

1. SSH into the server:
```bash
ssh corelink@your-server-ip
```

2. Edit the crontab:
```bash
crontab -e
```

3. Add this line to run every 5 minutes:
```bash
*/5 * * * * cd /home/corelink && /home/corelink/venv/bin/python manage.py oracle_periodic_update >> /home/corelink/logs/oracle_cron.log 2>&1
```

4. Save and exit (in nano: Ctrl+O, Enter, Ctrl+X)

### Option 2: System-wide Cron (if you have sudo access)

1. Create a new cron file:
```bash
sudo nano /etc/cron.d/corelink-oracle
```

2. Add this content:
```bash
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

*/5 * * * * corelink cd /home/corelink && /home/corelink/venv/bin/python manage.py oracle_periodic_update >> /home/corelink/logs/oracle_cron.log 2>&1
```

3. Set permissions:
```bash
sudo chmod 644 /etc/cron.d/corelink-oracle
```

## Log Monitoring

Create the logs directory:
```bash
mkdir -p /home/corelink/logs
```

View the cron log:
```bash
tail -f /home/corelink/logs/oracle_cron.log
```

## Command Options

The management command supports these options:

### Run with default settings (all active users):
```bash
python manage.py oracle_periodic_update
```

### Run only for recently active users (last 24 hours):
```bash
python manage.py oracle_periodic_update --recent-only
```

### Custom batch size:
```bash
python manage.py oracle_periodic_update --batch-size 50
```

## Real-time Updates (Already Configured)

The Oracle already triggers automatically on profile updates via Django signals in `profiles/signs.py`:

- When user adds/updates skills
- When user adds/updates credentials
- When user adds/updates projects
- When user adds/updates work experience
- When user adds/updates content posts
- When user updates social links or contact methods

No additional configuration needed for real-time updates - they work immediately after any profile change.

## Verification

### Check if cron is running:
```bash
sudo systemctl status cron
```

### List cron jobs:
```bash
crontab -l
```

### Test the command manually:
```bash
cd /home/corelink
source venv/bin/activate
python manage.py oracle_periodic_update
```

### Check recent cron logs:
```bash
grep "ORACLE" /home/corelink/logs/oracle_cron.log | tail -20
```

## Troubleshooting

### Cron not executing:
1. Check if cron service is running: `sudo systemctl status cron`
2. Verify the command path is correct: `which python`
3. Check logs for errors: `tail /home/corelink/logs/oracle_cron.log`

### Permission errors:
1. Ensure the log directory exists and is writable: `mkdir -p /home/corelink/logs && chmod 755 /home/corelink/logs`
2. Check file permissions on the project directory

### Database connection issues:
1. Ensure PostgreSQL is running
2. Check environment variables in `.env` file
3. Test database connection manually

## Performance Considerations

- The command processes users in batches (default 100 at a time)
- For 10,000 users, expect ~5-10 minutes per full run
- Using `--recent-only` significantly reduces processing time
- Cron runs every 5 minutes, but the command itself may take several minutes to complete
