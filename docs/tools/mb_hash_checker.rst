MalwareBazaar Hash Checker
##########################

Description
***********
The MalwareBazaar (MB) Hash Checker is taking a list of file hashes (SHA256), submits them to the MalwareBazaar database, and outputs results in a table with links to MalwareBazaar, a "found" flag that indicates whether each hash is known by MalwareBazaar, the number of malicious detections and the number of suspicious detections. 

.. image:: ../img/tools_mb_hash_checker.png
  :width: 1000
  :alt: img

Configuration
*************
This tool relies on the `MalwareBazaar API key <settings.html#malwarebazaar-api-key>`_ that you need to configure in the settings.

Notice that no limitation has been configured in the tool. You should check your MalwareBazaar subscription before using this tool.