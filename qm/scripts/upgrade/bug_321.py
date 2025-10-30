"""
Bug #321 - Locked analytics shouldn't have a next review date
This script removes the next review date from locked analytics
"""

from qm.models import Analytic, AnalyticMeta

def run():
    for analytic in Analytic.objects.filter(run_daily_lock=True):
        if analytic.analyticmeta.next_review_date is not None:
            analytic.analyticmeta.next_review_date = None
            analytic.analyticmeta.save()
            print(f" - Removed next review date for locked Analytic ID {analytic.id}")
