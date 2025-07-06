# TopMeteo Bot Deployment Guide

This Ansible playbook deploys the complete TopMeteo bot system on a remote host, including the Telegram bot, meteo crawler, systemd services, and cron jobs.

## Prerequisites

### On your local machine:
- Ansible installed (`pip install ansible`)
- SSH access to the target host
- SSH key configured for passwordless access

### On the target host:
- Ubuntu/Debian system
- User `rob` with sudo privileges
- SSH server running

## Files Structure

```
.
├── ansible_deploy.yml          # Main Ansible playbook
├── inventory.ini               # Ansible inventory
├── meteo_crawler.py            # Meteo crawler script
├── telegram_bot.py             # Telegram bot script
├── requirements_telegram.txt   # Python dependencies
├── README_telegram_bot.md      # Bot documentation
├── telegram_bot.service.j2     # Telegram bot systemd service template
├── meteo_crawler.service.j2    # Crawler systemd service template
├── env_template.j2             # Environment configuration template
├── logrotate.conf.j2           # Log rotation configuration
├── startup.sh.j2               # Management script template
└── README_deployment.md        # This file
```

## Deployment

### 1. Prepare the deployment

Ensure all required files are in the same directory as the playbook:

```bash
# Check that all files are present
ls -la *.py *.txt *.md *.j2 *.yml *.ini
```

### 2. Update configuration

Edit the following files if needed:

- `inventory.ini`: Update the target host IP if different
- `env_template.j2`: Update credentials and configuration
- `ansible_deploy.yml`: Modify paths or user if needed

### 3. Run the deployment

```bash
# Test the connection first
ansible -i inventory.ini meteo_bot -m ping

# Run the deployment
ansible-playbook -i inventory.ini ansible_deploy.yml
```

### 4. Verify deployment

SSH to the target host and check the installation:

```bash
ssh rob@192.168.2.212

# Check the installation
/opt/meteo_bot/startup.sh status

# Check services
sudo systemctl status telegram-bot
sudo systemctl status meteo-crawler

# Check cron jobs
crontab -l | grep meteo
```

## Directory Structure on Target Host

```
/opt/meteo_bot/
├── scripts/
│   ├── meteo_crawler.py
│   └── telegram_bot.py
├── data/
│   ├── day0/
│   ├── day1/
│   ├── day2/
│   ├── day3/
│   ├── day4/
│   └── day5/
├── logs/
│   ├── bot.log
│   └── crawler.log
├── config/
│   └── .env
├── venv/
│   └── (Python virtual environment)
├── requirements_telegram.txt
├── README_telegram_bot.md
└── startup.sh
```

## Services

### Telegram Bot Service
- **Service name**: `telegram-bot`
- **Status**: Automatically started and enabled
- **Logs**: `journalctl -u telegram-bot -f`
- **Restart**: `sudo systemctl restart telegram-bot`

### Meteo Crawler Service
- **Service name**: `meteo-crawler`
- **Status**: Enabled but not started (runs via cron)
- **Manual run**: `sudo systemctl start meteo-crawler`
- **Logs**: `journalctl -u meteo-crawler -f`

## Cron Jobs

The crawler runs automatically every 2 hours:
- **Schedule**: Every 2 hours at minute 0 (00:00, 02:00, 04:00, etc.)
- **Command**: Runs the crawler and logs to `/opt/meteo_bot/logs/crawler.log`
- **User**: `rob`

## Management Script

The deployment includes a management script at `/opt/meteo_bot/startup.sh`:

```bash
# Show status
/opt/meteo_bot/startup.sh status

# Run crawler manually
/opt/meteo_bot/startup.sh crawl

# Restart bot
/opt/meteo_bot/startup.sh restart

# Show logs
/opt/meteo_bot/startup.sh logs
/opt/meteo_bot/startup.sh logs crawler
/opt/meteo_bot/startup.sh logs systemd

# Show help
/opt/meteo_bot/startup.sh help
```

## Logs

- **Bot logs**: `/opt/meteo_bot/logs/bot.log`
- **Crawler logs**: `/opt/meteo_bot/logs/crawler.log`
- **Systemd logs**: `journalctl -u telegram-bot` or `journalctl -u meteo-crawler`
- **Log rotation**: Daily rotation, 30 days retention

## Security Features

The services run with security restrictions:
- **User**: Runs as `rob` user (non-root)
- **File system**: Protected with `ProtectSystem=strict`
- **Home directory**: Protected with `ProtectHome=true`
- **Privileges**: No new privileges allowed
- **Temporary files**: Private temporary directory

## Troubleshooting

### Check service status
```bash
sudo systemctl status telegram-bot
sudo systemctl status meteo-crawler
```

### Check logs
```bash
# Bot logs
tail -f /opt/meteo_bot/logs/bot.log

# Crawler logs
tail -f /opt/meteo_bot/logs/crawler.log

# Systemd logs
journalctl -u telegram-bot -f
```

### Manual crawler run
```bash
cd /opt/meteo_bot/scripts
/opt/meteo_bot/venv/bin/python meteo_crawler.py
```

### Check cron jobs
```bash
crontab -l
```

### Restart services
```bash
sudo systemctl restart telegram-bot
sudo systemctl restart meteo-crawler
```

## Updating

To update the deployment:

1. Update the source files
2. Re-run the Ansible playbook:
   ```bash
   ansible-playbook -i inventory.ini ansible_deploy.yml
   ```

The playbook is idempotent, so it's safe to run multiple times.

## Backup

Important files to backup:
- `/opt/meteo_bot/config/.env` (contains credentials)
- `/opt/meteo_bot/data/` (contains forecast images and PFD data)
- `/opt/meteo_bot/logs/` (contains log files)

## Monitoring

The system includes:
- **Service monitoring**: systemd automatically restarts failed services
- **Log rotation**: Automatic log rotation to prevent disk space issues
- **Cron monitoring**: Regular crawler execution every 2 hours
- **Status script**: Easy status checking with `/opt/meteo_bot/startup.sh status` 