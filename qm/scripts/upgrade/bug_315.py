"""
Bug #315 - Next review date should be set if status is updated to PUB
This script sets the next review date to today + 1 month for analytics with status PUB without next review date.
"""

from qm.models import Analytic, AnalyticMeta
from datetime import datetime, timedelta

def run():
    for analytic in Analytic.objects.filter(status='PUB', next_review_date__isnull=True):
        analytic.analyticmeta.next_review_date = datetime.now() + timedelta(days=30)
        print(f"Setting next review date for analytic {analytic.id} to {analytic.analyticmeta.next_review_date}")
        analytic.analyticmeta.save()
