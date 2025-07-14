VirusTotal Hash Checker
#######################

Description
***********
The VirusTotal (VT) Hash Checker is taking a list of file hashes (MD5, SHA1, SHA256), submits them to the VirusTotal database, and outputs results in a table with links to VT, a "found" flag that indicates whether each hash is known by VT, the number of malicious detections and the number of suspicious detections. 

.. image:: ../img/tools_vt_hash_checker.png
  :width: 1000
  :alt: img

Configuration
*************
This tool relies on the `VT API key <settings.html#vt-api-key>`_ that you need to configure in the settings.

Notice that no limitation has been configured in the tool. You should check your VT subscription before using this tool.