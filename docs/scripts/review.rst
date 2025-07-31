review.py
#########

Description
***********

The ``review.py`` script is used to update analytics to review, as defined in the `analytics workflow <../intro.html#analytic-workflow>`_.

It will automatically identified analytics that need to be reviewed based on the latest review and update their status accordingly.

Parameters
**********

You can set the ``DEBUG`` flag to `True` to see more detailed output during execution. This is useful for debugging purposes.

Execution
*********

This script is automatically started by the `run_campaign.sh <run_campaign.html>`_ script. It relies on the ``runscript`` command of the ``django-extensions`` package to be executed.

