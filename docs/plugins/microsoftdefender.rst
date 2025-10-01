Microsoft Defender
##################

Description
***********
This connector replaces the "microsoftsentinel" connector (https://learn.microsoft.com/en-us/azure/sentinel/move-to-defender).

Microsoft Defender provides a unified cybersecurity solution that integrates endpoint protection, cloud security, identity protection, email security, threat intelligence, exposure management, and SIEM into a centralized platform powered by a modern data lake.

This connector allows querying Microsoft Defender XDR logs using KQL (Kusto Query Language).

Queries have to return a "Computer" column, corresponding to either a native "Computer" field, or a transformation.

If a transformation is required, it has to be part of the "query" field (not in the "columns" field).
- You can define "Computer" by copying the value from another field: | project Computer = DstDvcHostname
- You can also truncate the computer name to remove the domain: | project Computer = tostring(split(Computer, ".")[0])

Queries can use the {{StartTimeISO}} and {{EndTimeISO}} placeholders to define the time range for the query. For example, you can use the following syntax to filter events from the last 14 days:

.. code-block:: 

    let starttime = todatetime('{{StartTimeISO}}');
    let endtime = todatetime('{{EndTimeISO}}');
    let lookback = starttime - 14d;

Requirements
************

- You'll need to install the msal package: ``pip install msal``
- The ``AdvancedHunting.Read.All`` permission is required for the APP ID.

Limitations
***********

The current implementation of the Microsoft Sentinel plugin does not support synchronizing rules. ``SYNC_RULES`` has to be set to ``False``. It does not get threats either.

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

SYNC_RULES
==========
- **Type**: boolean
- **Description**: Should the plugin synchronize rules? Currently, this feature is not supported, and this setting must be set to `False`.
- **Possible values**: True, False
- **Example**:

.. code-block:: python

    SYNC_RULES = False

QUERY_ERROR_INFO
================
- **Type**: string
- **Description**: Regular expression to identify if the query error message is an informational message (INFO) instead of an ERROR. This can be used to filter out non-critical errors in the logs. If empty, all messages will be considered errors.
- **Example**:

.. code-block:: python

    QUERY_ERROR_INFO = ".*(INFO|DEBUG).*"
