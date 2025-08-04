"""
FR #160 - Add a "last_time_seen" field to keep track of whether analytic have already triggered matches
Migration script to update the last_time_seen field in Analytic model
"""
from qm.models import Analytic, Snapshot
for analytic in Analytic.objects.all():
    snapshot = Snapshot.objects.filter(analytic=analytic, endpoint__isnull=False).order_by('-date').distinct()
    latest_snapshot = snapshot.first()
    if latest_snapshot:
        analytic.last_time_seen = latest_snapshot.date
        analytic.save()
