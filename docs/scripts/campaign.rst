campaign.py
###########

Description
***********

The ``campaign.py`` script runs the analytics daily to create `campaigns <../intro.html#campaigns-and-statistics>`_.

Parameters
**********

You can set the ``DEBUG`` flag to `True` to see more detailed output during execution. This is useful for debugging purposes.

Execution
*********

This script is automatically started by the `orchestrator.sh <orchestrator.html>`_ script. It relies on the ``runscript`` command of the ``django-extensions`` package to be executed.
