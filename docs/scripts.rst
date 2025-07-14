Scripts
#######

DeepHunter is shipped with some scripts, located under the ``./qm/scripts/`` folder.

- **backup.sh**: Used to do encrypted backups of the database and delete old backups (older than 3 months by default).
- **campaign.py**: Daily campaigns script, started from ``run_campaign.sh``. It relies on the ``runscript`` command of the ``django-extensions`` package.
- **optimize_db.sh**: Script to optimize the database after the ``run_campaign.sh`` script is executed.
- **run_campaign.sh**: Launcher for running "dynamic" threat hunting analytics and daily campaigns script.
- **upgrade.sh**: Script to upgrade DeepHunter when a new version is available on GitHub.
- **vulnerable_driver_name_detected_loldriver.py**: Script of the dynamic threat hunting analytic called ``vulnerable_driver_name_detected_loldriver.py``. It relies on the ``runscript`` command of the ``django-extensions`` package.
