"""
FR #301 - Remove the next_review_date for archived analytics
This script removes the next_review_date for all archived analytics.

To run:
$ source /data/venv/bin/activate
(venv) $ cd /data/deephunter/
(venv) $ python manage.py runscript upgrade.fr_301
"""

from qm.models import Analytic

def run():
    analytics = Analytic.objects.filter(status='ARCH')
    for analytic in analytics:
        if analytic.next_review_date is not None:
            analytic.next_review_date = None
            analytic.save()
            print(f"Removed next_review_date for archived analytic: {analytic.name}")