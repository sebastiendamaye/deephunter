Plugins: Active Directory
#########################

Settings
********

LDAP_SERVER
===========
- **Type**: string
- **Description**: LDAP server. Used to connect to the LDAP to gather additional information about a user based on a username (previously gathered by S1 using last logged in user), in the timeline view. To ignore the LDAP connection, set ``LDAP_SERVER`` to an empty string.
- **Example**:

.. code-block:: python

	# Set to empty string if you don't want to get additional user info from AD
	# LDAP_SERVER = ''
	LDAP_SERVER = 'gc.domain.com'
	
LDAP_PORT
=========
- **Type**: integer
- **Description**: LDAP port. Used to connect to the LDAP to gather additional information about a user based on a username (previously gathered by S1 using last logged in user), in the timeline view.
- **Example**:

.. code-block:: python
	
	LDAP_PORT = 636

LDAP_SSL
========
- **Type**: boolean
- **Possible values**: ``True`` or ``False``
- **Description**: Force the LDAP connection to use SSL. Used to connect to the LDAP to gather additional information about a user based on a username (previously gathered by S1 using last logged in user), in the timeline view.
- **Example**:

.. code-block:: python
	
	LDAP_SSL = True

LDAP_USER
=========
- **Type**: string
- **Format**: ``user@domain``
- **Description**: LDAP user (e.g., a service account). Used to connect to the LDAP to gather additional information about a username (previously gathered by S1 using last logged in user), in the timeline view.
- **Example**:

.. code-block:: python

	LDAP_USER = 'SRV12345@gad.domain.com'

LDAP_PWD
========
- **Type**: string
- **Description**: LDAP password associated to ``LDAP_USER``. Used to connect to the LDAP to gather additional information about a user based on a machine name, in the timeline view.
- **Example**:

.. code-block:: python

	LDAP_PWD = 'Awes0m3#P455w9rD'

LDAP_SEARCH_BASE
================
- **Type**: string
- **Description**: LDAP search base used to query the LDAP when searching for a user from a machine name. Usually composed of a serie of nested DC values.
- **Example**:

.. code-block:: python

	LDAP_SEARCH_BASE = 'DC=gad,DC=domain,DC=com'

LDAP_ATTRIBUTES
===============
- **Type**: string
- **Description**: LDAP attributes mapping. Expected values returned by the LDAP search should include the username, job title, business unit, office location, country. Depending on your LDAP architecture, fields could have different names. Use this mapping table to specify the corresponding fields.
- **Example**:

.. code-block:: python

	LDAP_ATTRIBUTES = {
		'USER_NAME': 'displayName',
		'JOB_TITLE': 'title',
		'BUSINESS_UNIT': 'division',
		'OFFICE': 'physicalDeliveryOfficeName',
		'COUNTRY': 'co'
	}
