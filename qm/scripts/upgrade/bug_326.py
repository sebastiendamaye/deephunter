"""
Bug #326 - Several analytics have last time seen date empty while there are events in the trend graph
This script populates the last time seen date for analytics that have events in the trend graph but have an empty last time seen date.
"""

from qm.models import Analytic, Snapshot

def run():
    for analytic in Analytic.objects.filter(analyticmeta__last_time_seen__isnull=True):
        snapshot = Snapshot.objects.filter(analytic=analytic, hits_count__gt=0).order_by('-date').first()
        if snapshot:
            analytic.analyticmeta.last_time_seen = snapshot.date
            analytic.analyticmeta.save()
            print(f" - Updated last time seen for Analytic ID #{analytic.id} to {snapshot.date}")
