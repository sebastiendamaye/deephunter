orchestrator.sh (launcher script)
#################################

Description
***********

The ``orchestrator.sh`` script is a launcher for running:

- "dynamic" threat hunting analytics (e.g., `vulnerable_driver_name_detected_loldriver.py <vulnerable_driver_name_detected_loldriver.html>`_),
- `campaign.sh <campaign.html>`_, and
- `review.py <review.html>`_.

Below is the code of this launcher:

.. code-block:: shell

    #!/bin/bash
    source /data/venv/bin/activate
    cd /data/deephunter/
    /data/venv/bin/python3 manage.py runscript vulnerable_driver_name_detected_loldriver
    /data/venv/bin/python3 manage.py runscript campaign
    /data/venv/bin/python3 manage.py runscript review
    deactivate

- **campaign.py**: Daily campaigns script, started from ``orchestrator.sh``. It relies on the ``runscript`` command of the ``django-extensions`` package.


Crontab
*******

It is recommended to schedule it using cron jobs to automate the backup process. An example is shown below.

.. code-block:: shell

    # m h  dom mon dow   command
    1  0 * * *      /data/deephunter/qm/scripts/orchestrator.sh
