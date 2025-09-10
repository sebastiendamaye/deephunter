"""
FR #210 - Add trend and sparkline to dashboard widgets
This script updates the nb_analytics field for existing Campaigns to reflect the total number of TH analytics at the time of each campaign.

To run:
$ source /data/venv/bin/activate
(venv) $ cd /data/deephunter/
(venv) $ python manage.py runscript upgrade.fr_210
"""

from qm.models import Campaign, Analytic
from datetime import datetime
from django.utils import timezone

def run():
    for campaign in Campaign.objects.filter(name__startswith='daily_cron'):
        campaign_date = datetime.strptime(campaign.name.split('_')[2], '%Y-%m-%d')
        campaign_date = timezone.make_aware(campaign_date, timezone.get_current_timezone())
        count = Analytic.objects.exclude(status='ARCH').filter(pub_date__lte=campaign_date).count()
        campaign.nb_analytics = count
        campaign.save()