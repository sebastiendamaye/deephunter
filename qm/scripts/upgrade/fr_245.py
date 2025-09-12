"""
FR #245 - Development of the microsoftdefender connector to replace microsoftsentinel one
This script creates the MS Defender connector and its parameters in the DB.

To run:
$ source /data/venv/bin/activate
(venv) $ cd /data/deephunter/
(venv) $ python manage.py runscript upgrade.fr_245
"""

from connectors.models import Connector, ConnectorConf
from qm.models import Analytic

def run():
    # Create the MS Defender connector
    description = """This connector replaces the "microsoftsentinel" connector (legacy). Notice that it requires the "AdvancedHunting.Read.All" permission.

Microsoft Defender provides a unified cybersecurity solution that integrates endpoint protection, cloud security, identity protection, email security, threat intelligence, exposure management, and SIEM into a centralized platform powered by a modern data lake."""

    connector = Connector.objects.create(
        name='microsoftdefender',
        description=description,
        enabled=False,
        domain='analytics'
    )

    # Create its parameters
    ConnectorConf.objects.create(
        connector=connector,
        key='TENANT_ID',
        value='*************',
        description='MS Defender Tenant ID / Directory ID'
    )
    ConnectorConf.objects.create(
        connector=connector,
        key='CLIENT_ID',
        value='*************',
        description='MS Defender APP ID / CLIENT ID'
    )
    ConnectorConf.objects.create(
        connector=connector,
        key='CLIENT_SECRET',
        value='************',
        description='Password associated to the APP ID',
    )
    ConnectorConf.objects.create(
        connector=connector,
        key='SYNC_RULES',
        value='False',
        description='If set to True, DeepHunter will automatically synchronize your threat hunting analytics (create, modify or delete) with corresponding rules in MS Defender XDR. Possible values: True|False',
    )
    ConnectorConf.objects.create(
        connector=connector,
        key='QUERY_ERROR_INFO',
        value='',
        description='Regular expression to filter what should be considered INFO instead of ERROR in query error message',
    )
