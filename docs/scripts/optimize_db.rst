optimize_db.sh
##############

Description
***********

The ``optimize_db.sh`` script is used to optimize the database after the ``orchestrator.sh`` script is executed.

Crontab
*******

It is recommended to schedule it using cron jobs. An example is shown below.

.. code-block:: shell

    # m h  dom mon dow   command
    0  2 * * *      /data/deephunter/qm/scripts/optimize_db.sh
