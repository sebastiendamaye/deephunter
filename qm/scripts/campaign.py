from django.conf import settings
from datetime import datetime, timedelta
from qm.models import Snapshot, Campaign
from qm.utils import run_campaign

DB_DATA_RETENTION = settings.DB_DATA_RETENTION

DEBUG = False

def run():

    # Cleanup all campaigns older than DB_DATA_RETENTION (90 days by default). Will automatically cascade delete snapshots and endpoints
    # Date of campaign is when the script runs (today) while snapshot date is the day before (detection date)
    Campaign.objects.filter(date_start__lt=datetime.today()-timedelta(days=DB_DATA_RETENTION)).delete()
    # Make sure remaining old Snapshots/Endpoints are also deleted (when regen stats is used, campaign date is today, while 1st stats are 3 months old)
    Snapshot.objects.filter(date__lt=datetime.today()-timedelta(days=DB_DATA_RETENTION)).delete()

    # Run campaign by calling the run_campaign function (no date provided will default to today)
    run_campaign(debug=DEBUG)
