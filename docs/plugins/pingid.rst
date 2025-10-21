PingID
######

Description
***********
PingID is a multi-factor authentication (MFA) service from Ping Identity that adds an extra layer of security to user sign-ins. It is a cloud-based service that uses a mobile app and various methods like push notifications, one-time passcodes (OTPs) via SMS or email, and QR codes to verify user identities, making it more secure than just a password. This service is used for both workforce (employees, contractors) and customer identity management.

This plugin integrates PingID as an authentication method in DeepHunter.

Settings
********

CLIENT_ID
=========

- **Type**: string
- **Description**: The Client ID provided by PingID for OAuth2 authentication.
- **Example**: 

.. code-block:: python

	CLIENT_ID = 'deephunter'

CLIENT_SECRET
=============

- **Type**: string
- **Description**: The Client Secret provided by PingID for OAuth2 authentication.
- **Example**: 

.. code-block:: python

	CLIENT_SECRET = 'aB9cD3eF7gH1iJ2kL0mN4pQ6rS8tU5vWzYxZ3A7bC9dE2fG1hI0jsUQK3lM6nP9q'

SERVER_METADATA_URL
===================

- **Type**: string
- **Description**: The Server Metadata URL for PingID.
- **Example**: 

.. code-block:: python

    SERVER_METADATA_URL = 'https://ping-sso.domains.com/.well-known/openid-configuration'

SCOPE
=====

- **Type**: string
- **Description**: Scope parameters (separated by spaces) gathered as output to the authentication request.
- **Example**: 

.. code-block:: python

	SCOPE = 'openid groups profile email'

AUTH_TOKEN_MAPPING_USERNAME
===========================

- **Type**: string
- **Description**: Mapping of expected keys (left) vs token fields (right). It is recommended to use the debug return function of  ``./deephunter/views.py`` on line 55 to check the token values. Only modify values (right side), not the keys (left).
- **Example**: 

.. code-block:: python

	AUTH_TOKEN_MAPPING_USERNAME = 'sub'

AUTH_TOKEN_MAPPING_FIRST_NAME
=============================

- **Type**: string
- **Description**: Mapping of expected keys (left) vs token fields (right). It is recommended to use the debug return function of  ``./deephunter/views.py`` on line 55 to check the token values. Only modify values (right side), not the keys (left).
- **Example**: 

.. code-block:: python

	AUTH_TOKEN_MAPPING_FIRST_NAME = 'firstName',

AUTH_TOKEN_MAPPING_LAST_NAME
============================

- **Type**: string
- **Description**: Mapping of expected keys (left) vs token fields (right). It is recommended to use the debug return function of  ``./deephunter/views.py`` on line 55 to check the token values. Only modify values (right side), not the keys (left).
- **Example**: 

.. code-block:: python

	AUTH_TOKEN_MAPPING_LAST_NAME = 'lastName'

AUTH_TOKEN_MAPPING_EMAIL
========================

- **Type**: string
- **Description**: Mapping of expected keys (left) vs token fields (right). It is recommended to use the debug return function of  ``./deephunter/views.py`` on line 55 to check the token values. Only modify values (right side), not the keys (left).
- **Example**: 

.. code-block:: python

	AUTH_TOKEN_MAPPING_EMAIL = 'email'

AUTH_TOKEN_MAPPING_GROUPS
=========================

- **Type**: string
- **Description**: Mapping of expected keys (left) vs token fields (right). It is recommended to use the debug return function of  ``./deephunter/views.py`` on line 55 to check the token values. Only modify values (right side), not the keys (left).
- **Example**: 

.. code-block:: python

	AUTH_TOKEN_MAPPING_GROUPS = 'groups'

USER_GROUPS_MEMBERSHIP
======================

- **Type**: Dictionary
- **Description**: This variable is used to map local groups with AD groups.
- **Example**: 

.. code-block:: python

	USER_GROUPS_MEMBERSHIP = {
		'viewer': 'deephunter_read',
		'manager': 'deephunter_write'
	}
