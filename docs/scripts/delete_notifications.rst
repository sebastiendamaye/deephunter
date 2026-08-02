delete_notifications.py
#######################

Description
***********

The ``delete_notifications.py`` script removes old notifications from the database.

Parameters
**********

You can set the ``DEBUG`` flag to `True` to see more detailed output during execution. This is useful for debugging purposes.

The ``AUTO_DELETE_NOTIFICATIONS_AFTER`` setting controls how long notifications are kept in the database before being automatically deleted. It is a dictionary that maps notification levels to the number of days to retain them. The default values are as follows:

.. code-block:: python

    AUTO_DELETE_NOTIFICATIONS_AFTER = {
        'debug':   1,
        'info':    7,
        'success': 7,
        'warning': 30,
        'error':   30,
    }

Execution
*********

This script is automatically started by the `orchestrator.sh <orchestrator.html>`_ script. It relies on the ``runscript`` command of the ``django-extensions`` package to be executed.
