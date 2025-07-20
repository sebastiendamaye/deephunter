Authentication, Groups and Privileges
#####################################

Authentication modes
********************
DeepHunter currently supports 3 authentication modes:

- **local**: this is the native Django authentication where usernames and passwords are stored in the local database.
- **PingID**: this authentication relies on `PingIdentity Single Sign-On <https://www.pingidentity.com/en/platform/capabilities/single-sign-on.html>`_.
- **Entra ID**: this authentication relies on `Microsoft Entra ID <https://learn.microsoft.com/en-us/entra/fundamentals/whatis>`_.

The login screen will look as follows if you haven't set ``LOGIN_FORM`` to ``False`` in the settings. Else, only the ``Login with SSO`` link will appear.

.. image:: img/login.png
  :width: 300
  :alt: DeepHunter login form

Local authentication
********************
This is the native Django authentication. Start by creating a super user

.. code-block::

	$ source /data/venv/bin/activate
	(venv) $ ./manage.py createsuperuser

Once a super user has been created, you should be able to access the backend of DeepHunter (``https://deephunter_url/admin``) and manage groups and users.

PingID
******

To use PingID:

- modify the necessary settings (check the `settings <settings.html#authlib-oauth-clients>`_ page) related to PingID configuration.
- set ``AUTH_PROVIDER`` to ``pingid``.
- Create 2 Active Directory (AD) groups: for example ``deephunter_usr`` (standard user, with read-only access) and ``deephunter_pr`` (privileged users, i.e., administrators) and assign users to these groups.
- In the settings, do the correct mapping for the ``USER_GROUPS_MEMBERSHIP`` variable.
- You'll need to assign correct values for the ``AUTH_TOKEN_MAPPING`` variable. You can use the debug return function of ``./deephunter/views.py`` on line 64 to check the token values to do this mapping.
- Optionnaly disable the login form (set ``LOGIN_FORM`` to ``False`` in the settings)
- When a user logs in, if the authentication is successful, information from AD will be gathered to update the user in the local database.

Entra ID
********

To use Entra ID:

- modify the necessary settings (check the `settings <settings.html#authlib-oauth-clients>`_ page) related to Entra ID configuration.
- set ``AUTH_PROVIDER`` to ``entra_id``.
- Create roles in Entra ID, for example ``deephunter_usr`` (standard user, with read-only access) and ``deephunter_pr`` (privileged users, i.e., administrators) and assign users one of these roles.
- In the settings, do the correct mapping for the ``USER_GROUPS_MEMBERSHIP`` variable.
- You'll need to assign correct values for the ``AUTH_TOKEN_MAPPING`` variable. You can use the debug return function of ``./deephunter/views.py`` on line 64 to check the token values to do this mapping.
- Optionnaly disable the login form (set ``LOGIN_FORM`` to ``False`` in the settings)
- When a user logs in, if the authentication is successful, information from the session token will be gathered to update the user in the local database.

Groups and Privileges
*********************
Use the `authgroup fixture <install.html#install-initial-data>`_ to create necessary groups in the local database.

Users are intended to be assigned to one of these local groups:

- **viewer**: read-only user (all of the ``can_view`` permissions of the ``qm`` model). You can change default permissions if needed.
- **manager**: write-access user (all permissions of the ``qm`` model).

Note that administrators have the ``manager`` profile, with the ``Superuser status`` option enabled (automatically assigned during first login, based on the AD group the user belongs to, if you are relying in PingID).

In the settings, do the correct mapping for the ``USER_GROUPS_MEMBERSHIP`` variable.
