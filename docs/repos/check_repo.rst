Check a repository
##################

This allows you to check the status of an existing repository. It is recommended to perform this action prior to importing analytics from a repo (``import`` button).

It will perform various checks, including:

- Validating repository access
- Checking the JSON format
- Checking analytics consistency (see `expected format <index.html#expected-format-for-repositories>`_)

The **check** operation won't apply any change to your database. It will only perform checks.

This process is done in the background (it will continue running even if you leave the page). You can stop it anytime by clicking the "CANCEL" button.

.. image:: ../img/check_repo.png
  :alt: check repo

After checking the remote repositories, a `report <report.html>`_ will be created.
