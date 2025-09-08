#!/bin/bash
# 0 7 * * * /data/deephunter/backup.sh
# deletes old backups (older than 3 months)
/usr/bin/find /data/backups -name "*.dump.gpg" -type f -mtime +90 -exec rm -f {} \;
# encrypted backup of the DB
source /data/venv/bin/activate
cd /data/deephunter/
/data/venv/bin/python3 manage.py dbbackup --encrypt --output-path "/data/backups/default-$(hostname)-$(date +%F-%H%M%S).dump.gpg"