from django.conf import settings
from qm.models import Analytic
from datetime import datetime, timedelta
from notifications.utils import add_info_notification

# Workflow settings
DAYS_BEFORE_REVIEW = settings.DAYS_BEFORE_REVIEW
DISABLE_ANALYTIC_ON_REVIEW = settings.DISABLE_ANALYTIC_ON_REVIEW

DEBUG = False

def run():

    analytics = Analytic.objects.filter(
        run_daily_lock=False,
        status='PUB',
        next_review_date__lte=datetime.now()
        )
    
    for analytic in analytics:
        
        analytic.status = 'REVIEW'
        
        if DISABLE_ANALYTIC_ON_REVIEW:
            analytic.run_daily = False
        
        if DEBUG:
            print(f"{analytic.name} set to REVIEW with RUN_DAILY set to {analytic.run_daily}")

        analytic.save()

    if analytics.count() > 0:
        add_info_notification(f"{analytics.count()} analytics marked as 'to be reviewed'")
    