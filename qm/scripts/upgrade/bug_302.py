"""
Bug #302 - Regenerating stats of an analytic that has the run_daily flag set removes the analytic from the campaign run analytics counter
This script populates the campaign.nb_endpoints field and the CampaignCompletion table for all campaigns.
"""

from qm.models import Campaign, CampaignCompletion, Endpoint, Snapshot
from connectors.models import Connector

def run():
    for campaign in Campaign.objects.filter(name__startswith="daily_cron"):
        if not campaign.nb_endpoints:
            campaign.nb_endpoints = Endpoint.objects.filter(snapshot__campaign=campaign).distinct().count()
            campaign.save()
            print(f"Campaign {campaign.name} updated: {campaign.nb_endpoints} distinct endpoints")
        else:
            print(f"Campaign {campaign.name} already has nb_endpoints set")

        for connector in Connector.objects.filter(domain="analytics", enabled=True):
            campaigncompletion, created = CampaignCompletion.objects.get_or_create(
                campaign=campaign,
                connector=connector,
                defaults={
                'nb_queries_complete': Snapshot.objects.filter(campaign=campaign, analytic__connector=connector).count()
            })
            campaigncompletion.save()
            if created:
                print(f"Created CampaignCompletion for campaign {campaign.name} / connector {connector.name}: {campaigncompletion.nb_queries_complete}")
            else:
                print(f"CampaignCompletion already exists for campaign {campaign.name} / connector {connector.name}")
        print("----------")
