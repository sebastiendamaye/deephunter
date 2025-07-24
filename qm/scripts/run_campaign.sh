#!/bin/bash
# 30 5 * * * /data/deephunter/run_campaign.sh
source /data/venv/bin/activate
cd /data/deephunter/
/data/venv/bin/python3 manage.py runscript vulnerable_driver_name_detected_loldriver
/data/venv/bin/python3 manage.py runscript campaign
/data/venv/bin/python3 manage.py runscript review
deactivate
