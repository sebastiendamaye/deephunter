from django.conf import settings
from qm.models import Analytic
from datetime import datetime, timedelta
import logging

# Workflow settings
DAYS_BEFORE_REVIEW = settings.DAYS_BEFORE_REVIEW
DISABLE_ANALYTIC_ON_REVIEW = settings.DISABLE_ANALYTIC_ON_REVIEW

DEBUG = False

# Get an instance of a logger
logger = logging.getLogger(__name__)

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

