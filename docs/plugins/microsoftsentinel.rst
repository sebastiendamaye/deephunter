Microsoft Sentinel
###########################

Description
***********
Microsoft Sentinel is a scalable, cloud-native security information and event management (SIEM) that delivers an intelligent and comprehensive solution for SIEM and security orchestration, automation, and response (SOAR). Microsoft Sentinel provides cyberthreat detection, investigation, response, and proactive hunting, with a bird's-eye view across your enterprise.

This connector allows querying Microsoft Sentinel logs using KQL (Kusto Query Language).

Queries have to return a "Computer" column, corresponding to either a native "Computer" field, or a transformation. If a transformation is required, it has to be part of the "query" field (not in the "columns" field).

- You can define "Computer" by copying the value from another field: ``| project Computer = DstDvcHostname``
- You can also truncate the computer name to remove the domain: ``| project Computer = tostring(split(Computer, ".")[0])``

Limitations
***********

The current implementation of the Microsoft Sentinel plugin does not support synchronizing rules. ``SYNC_RULES`` has to be set to ``False``.

Settings
********

TENANT_ID
=========
- **Type**: string
- **Description**: Tenant ID
- **Example**:

.. code-block:: python

    TENANT_ID = "a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6"

CLIENT_ID
=========
- **Type**: string
- **Description**: Client ID of the application registered in Azure Active Directory. This is used for authentication when connecting to Microsoft Sentinel.
- **Example**:

.. code-block:: python

    CLIENT_ID = "b1c2d3e4-f5a6-7b8c-9d0e-f1a2b3c4d5e6"

CLIENT_SECRET
=============
- **Type**: string
- **Description**: Password associated with the client ID. This is used for authentication when connecting to Microsoft Sentinel. 
- **Example**:

.. code-block:: python

    CLIENT_SECRET = "s3cr3t-k3y-v4lue"

WORKSPACE_ID
============
- **Type**: string
- **Description**: The unique identifier of the Microsoft Sentinel workspace. This is required to connect to the specific Sentinel instance. 
- **Example**:

.. code-block:: python

    WORKSPACE_ID = "w1x2y3z4-a5b6-c7d8-e9f0-g1h2i3j4k5l6"

SYNC_RULES
==========
- **Type**: boolean
- **Description**: Should the plugin synchronize rules? Currently, this feature is not supported, and this setting must be set to `False`.
- **Possible values**: True, False
- **Example**:

.. code-block:: python

    SYNC_RULES = False

SUBSCRIPTION_ID
===============
- **Type**: string
- **Description**: The Azure subscription ID where the Microsoft Sentinel workspace is located. This is used to identify the subscription for API calls and resource management. 
- **Example**:

.. code-block:: python

    SUBSCRIPTION_ID = "w1x2y3z4-a5b6-c7d8-e9f0-g1h2i3j4k5l6"

RESOURCE_GROUP
==============
- **Type**: string
- **Description**: The name of the Azure resource group that contains the Microsoft Sentinel workspace. This is used to organize and manage resources in Azure. 
- **Example**:

.. code-block:: python

    RESOURCE_GROUP = "my_resource_group"

WORKSPACE_NAME
==============
- **Type**: string
- **Description**: The name of the Microsoft Sentinel workspace. This is used to identify the workspace within the specified resource group and subscription. 
- **Example**:

.. code-block:: python

    WORKSPACE_NAME = "myWorkspaceName"
