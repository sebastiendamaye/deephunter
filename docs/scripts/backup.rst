backup.sh
#########

Description
***********

The ``backup.sh`` script is used to perform encrypted backups of the DeepHunter database and to delete old backups (older than 3 months by default).

This script is essential for maintaining data integrity and ensuring that you have recoverable copies of your database.

Crontab
*******

It is recommended to schedule it using cron jobs to automate the backup process. An example is shown below.

.. code-block:: shell

    # m h  dom mon dow   command
    0  4 * * *      /data/deephunter/qm/scripts/backup.sh

