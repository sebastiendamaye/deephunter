Entra ID
########

Description
***********
Entra ID is the new name for Microsoft's cloud-based identity and access management service, formerly known as Azure Active Directory. It helps organizations manage and secure user identities to control access to applications, data, and resources across multicloud and on-premises environments. Entra ID uses Zero Trust principles to ensure that only authenticated and authorized users can access what they need.

This plugin integrates Entra ID as an authentication method in DeepHunter.

Settings
********

CLIENT_ID
=========

- **Type**: string
- **Description**: The Client ID provided by Entra ID for OAuth2 authentication.
- **Example**: 

.. code-block:: python

	CLIENT_ID = 'deephunter-client-id'

CLIENT_SECRET
=============

- **Type**: string
- **Description**: The Client Secret provided by Entra ID for OAuth2 authentication.
- **Example**: 

.. code-block:: python

	CLIENT_SECRET = 'Ji0AA8tXKn6wnC9Vf7a211ykaMor5s'

SERVER_METADATA_URL
===================

- **Type**: string
- **Description**: The Server Metadata URL for Entra ID.
- **Example**: 

.. code-block:: python

    SERVER_METADATA_URL = 'https://login.microsoftonline.com/lmgh5678-12j4-97s2-n5b4-85f53h902k31/.well-known/openid-configuration'

SCOPE
=====

- **Type**: string
- **Description**: Scope parameters (separated by spaces) gathered as output to the authentication request.
- **Example**: 

.. code-block:: python

	SCOPE = 'openid profile email'
	
AUTH_TOKEN_MAPPING_USERNAME
===========================

- **Type**: string
- **Description**: Mapping of expected keys (left) vs token fields (right). It is recommended to use the debug return function of  ``./deephunter/views.py`` on line 55 to check the token values. Only modify values (right side), not the keys (left).
- **Example**: 

.. code-block:: python

	AUTH_TOKEN_MAPPING_USERNAME = 'unique_name'

AUTH_TOKEN_MAPPING_FIRST_NAME
=============================

- **Type**: string
- **Description**: Mapping of expected keys (left) vs token fields (right). It is recommended to use the debug return function of  ``./deephunter/views.py`` on line 55 to check the token values. Only modify values (right side), not the keys (left).
- **Example**: 

.. code-block:: python

	AUTH_TOKEN_MAPPING_FIRST_NAME = 'given_name',

AUTH_TOKEN_MAPPING_LAST_NAME
============================

- **Type**: string
- **Description**: Mapping of expected keys (left) vs token fields (right). It is recommended to use the debug return function of  ``./deephunter/views.py`` on line 55 to check the token values. Only modify values (right side), not the keys (left).
- **Example**: 

.. code-block:: python

	AUTH_TOKEN_MAPPING_LAST_NAME = 'family_name'

AUTH_TOKEN_MAPPING_EMAIL
========================

- **Type**: string
- **Description**: Mapping of expected keys (left) vs token fields (right). It is recommended to use the debug return function of  ``./deephunter/views.py`` on line 55 to check the token values. Only modify values (right side), not the keys (left).
- **Example**: 

.. code-block:: python

	AUTH_TOKEN_MAPPING_EMAIL = 'upn'

AUTH_TOKEN_MAPPING_GROUPS
=========================

- **Type**: string
- **Description**: Mapping of expected keys (left) vs token fields (right). It is recommended to use the debug return function of  ``./deephunter/views.py`` on line 55 to check the token values. Only modify values (right side), not the keys (left).
- **Example**: 

.. code-block:: python

	AUTH_TOKEN_MAPPING_GROUPS = 'roles'

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
