"""
FR #275 - Develop a connectors catalog so that connectors do not have to be installed even if not enabled
This script adds the missing domain values in the Connector model and sets installed=True for all enabled connectors.

To run:
$ source /data/venv/bin/activate
(venv) $ cd /data/deephunter/
(venv) $ python manage.py runscript upgrade.fr_275
"""

from connectors.models import Connector

def run():

    # Update domain values for existing connectors
    connector_names = ['activedirectory', 'loldrivers', 'malwarebazaar', 'virustotal', 'whois']
    for connector_name in connector_names:
        connector = Connector.objects.get(name=connector_name)
        connector.domain = 'extensions'
        connector.save()
        print(f"Updated domain for connector: {connector_name}")

    # Set installed=True for all enabled connectors
    for connector in Connector.objects.filter(enabled=True):
        if not connector.installed:
            connector.installed = True
            connector.save()
            print(f"Set installed=True for enabled connector: {connector.name}")
