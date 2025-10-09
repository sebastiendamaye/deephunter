"""
FR #61 - Community repo for threat hunting analytics
Migration script to populate the ConnectorDomain and Connector models
"""
from connectors.models import Connector

def run():
    connector = Connector.objects.get(name="microsoftsentinel")
    connector.domain = "analytics"
    connector.save()

    connector = Connector.objects.get(name="sentinelone")
    connector.domain = "analytics"
    connector.save()

    connector = Connector(name="github", description="Github repo sync", domain="repos")
    connector.save()

    connector = Connector(name="bitbucket", description="Bitbucket repo sync", domain="repos")
    connector.save()
