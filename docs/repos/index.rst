Repos
#####

Description
***********
DeepHunter analytics can be directly imported from a GitHub or BitBucket repository.

You can access the `list repos <list_repos.html>`_ view from the menu (**Admin > Manage repos**) to manage your repositories.

Default values can be set in the settings:

- `REPO_IMPORT_CREATE_FIELD_IF_NOT_EXIST <../settings.html#repo-import-create-field-if-not-exist>`_
- `REPO_IMPORT_DEFAULT_STATUS <../settings.html#repo-import-default-status>`_
- `REPO_IMPORT_DEFAULT_RUN_DAILY <../settings.html#repo-import-default-run-daily>`_

Expected format for repositories
********************************

JSON files
==========

Repositories currently supported are public GitHub and BitBucket repositories.

Analytics should be JSON files, with the following structure:

.. list-table::
   :widths: 100 600 20
   :header-rows: 1

   * - Key
     - Description
     - M/O*
   * - ``version``
     - Version of the analytic (it won't be used by DeepHunter)
     - O
   * - ``name``
     - Analytic name (usually the same name as the JSON file, but without the ``*.json`` extension)
     - M
   * - ``description``
     - Description of the analytic
     - O
   * - ``notes``
     - Threat hunting notes
     - O
   * - ``confidence``
     - Confidence level of the analytic (1-5). Default to 1 if out-of-band, or if nor present.
     - O
   * - ``relevance``
     - Relevance level of the analytic (1-5). Default to 1 if out-of-band, or if nor present.
     - O
   * - ``category``
     - Category of the analytic (e.g. "detect", "triage", "threat hunting").
     - O
   * - ``connector``
     - Connector type (e.g. "sentinelone", "microsoftsentinel").
     - M
   * - ``query``
     - Analytic's query
     - M
   * - ``columns``
     - Optional columns associated to the analytic's query
     - O
   * - ``emulation_validation``
     - Emulation plan validation
     - O
   * - ``references``
     - List of html links, separated by commas
     - O
   * - ``mitre_techniques``
     - List of MITRE techniques, separated by commas
     - O
   * - ``threats``
     - List of threats, separated by commas
     - O
   * - ``actors``
     - List of threat actors, separated by commas
     - O
   * - ``target_os``
     - List of target operating systems, separated by commas
     - O
   * - ``vulnerabilities``
     - List of vulnerabilities, separated by commas
     - O
(*) Optional/Mandatory

Example
=======
Below is an example of a valid analytic JSON file:

.. code-block:: json

   {
      "version": 1,
      "name": "psexec_connect",
      "description": "Detects use of psexec",
      "notes": "- To move around freely without attracting too much attention, attackers often use reliable software (one of the favorites is psexec) that looks normal in an enterprise environment.\r\n- Use the following aggregate to easily group by endpoint: `| group array_agg_distinct(dst.ip.address) by endpoint.name, src.process.cmdline`",
      "confidence": 2,
      "relevance": 3,
      "category": "detect",
      "connector": "sentinelone",
      "query": "endpoint.os = 'windows'\r\nand event.type = 'IP Connect'\r\nand src.process.name matches 'psexec\\\\.exe'",
      "columns": "| columns event.time, event.type, site.name, agent.uuid, src.process.storyline.id, src.process.user, src.process.uid, src.process.cmdline, src.ip.address, src.port.number, dst.ip.address, dst.port.number, src.process.parent.cmdline, tgt.process.cmdline",
      "emulation_validation": "",
      "references": "https://theitbros.com/using-psexec-to-run-commands-remotely/\r\nhttps://redcanary.com/blog/threat-hunting-psexec-lateral-movement/",
      "mitre_techniques": [
         "T1569.002",
         "T1570"
      ],
      "threats": [],
      "actors": [],
      "target_os": [
         "windows"
      ],
      "vulnerabilities": []
   }


Contents
********

.. toctree::
   :maxdepth: 1
  
   list_repos
   add_repo
   edit_repo
   delete_repo
   check_repo
   import_repo
   report
