from django.conf import settings
from datetime import datetime, timedelta
import numpy as np
from scipy import stats
from math import isnan
from qm.models import Analytic, Snapshot, Campaign, Endpoint, TasksStatus
from qm.utils import run_campaign, get_campaign_date
import logging
import requests
from celery import shared_task
from django.shortcuts import get_object_or_404
from time import sleep

# Dynamically import all connectors
import importlib
import pkgutil
import plugins
all_connectors = {}
for loader, module_name, is_pkg in pkgutil.iter_modules(plugins.__path__):
    module = importlib.import_module(f"plugins.{module_name}")
    all_connectors[module_name] = module


PROXY = settings.PROXY
DB_DATA_RETENTION = settings.DB_DATA_RETENTION
CAMPAIGN_MAX_HOSTS_THRESHOLD = settings.CAMPAIGN_MAX_HOSTS_THRESHOLD
ON_MAXHOSTS_REACHED = settings.ON_MAXHOSTS_REACHED
DISABLE_RUN_DAILY_ON_ERROR = settings.DISABLE_RUN_DAILY_ON_ERROR

# Get an instance of a logger
logger = logging.getLogger(__name__)


@shared_task()
def regenerate_stats(analytic_id):
    analytic = get_object_or_404(Analytic, pk=analytic_id)

    # we assume that analytic won't fail (flag will be set later if analytic fails)
    analytic.query_error = False
    analytic.query_error_message = ''
    analytic.save()
    
    # Create Campaign
    # Date of campaign is when the script runs (today) while snapshot date is the day before (detection date)
    campaign = Campaign(
        name='regenerate_stats_{}_{}'.format(analytic.name, datetime.now().strftime("%Y-%m-%d-%H-%M")),
        description='Regenerate stats for {}'.format(analytic.name),
        date_start=datetime.now(),
        nb_queries=1
        )
    campaign.save()

    # Get task in TasksStatus object
    celery_status = get_object_or_404(TasksStatus, taskname=analytic.name)

    # Delete all snapshots for this analytic
    # (related Endpoint object will automatically cascade delete)
    Snapshot.objects.filter(analytic=analytic).delete()
    
    # Rebuild campaigns for last DB_DATA_RETENTION (90 days by default) for the analytic
    for days in reversed(range(DB_DATA_RETENTION)):
        
        # store current time (used to update snapshot runtime)
        start_runtime = datetime.now()

        # Call the "query" function of the appropriate connector
        # (no date range provided, so it will use the last 24 hours by default)
        todate = datetime.combine((datetime.now() - timedelta(days=days)), datetime.min.time())
        fromdate = (todate - timedelta(days=1))
        data = all_connectors.get(analytic.connector.name).query(analytic, fromdate.isoformat(), todate.isoformat())

        # store current time (used to update snapshot runtime)
        end_runtime = datetime.now()

        # Create snapshot. Necessary to have the object to link the detected assets.
        # Stats will be updated later to the snaptshot
        # the date of the snapshot is the day before the campaign (detection date)
        snapshot = Snapshot(
            campaign=campaign,
            analytic=analytic,
            date=todate - timedelta(days=1),
            runtime = (end_runtime-start_runtime).total_seconds()
            )
        snapshot.save()

        if len(data) != 0:

            hits_endpoints = len(data)
            hits_count = 0
            
            for i in data:
                
                # The storylineid field has 255 chars max
                if len(i[3]) < 255:
                    storylineid = i[3][1:][:-1]
                else:
                    storylineid = ''
                
                # update detected endpoints and link it with current snapshot
                endpoint = Endpoint(
                    hostname = i[0],
                    site = i[1],
                    snapshot = snapshot,
                    storylineid = storylineid
                )
                endpoint.save()
                # count nb of hits
                hits_count += int(float(i[2]))
        else:
            hits_count = 0
            hits_endpoints = 0
        
        # Now that stats have been collected, snapshot is updated.
        snapshot.hits_count = hits_count
        snapshot.hits_endpoints = hits_endpoints
        snapshot.save()
        
        # When the max_hosts threshold is reached (by default 1000)
        if hits_endpoints >= CAMPAIGN_MAX_HOSTS_THRESHOLD:
            # Update the maxhost counter if reached
            analytic.maxhosts_count += 1
            # if threshold is reached
            if analytic.maxhosts_count >= ON_MAXHOSTS_REACHED['THRESHOLD']:
                # If DISABLE_RUN_DAILY is set and run_daily_lock is not set, we disable the run_daily flag for the analytic
                if ON_MAXHOSTS_REACHED['DISABLE_RUN_DAILY'] and not analytic.run_daily_lock:
                    analytic.run_daily = False
                # If DELETE_STATS is set and run_daily_lock is not set, we delete all stats for the analytic
                if ON_MAXHOSTS_REACHED['DELETE_STATS'] and not analytic.run_daily_lock:
                    Snapshot.objects.filter(analytic=analytic).delete()
            # we update the analytic (counter updated, and flags updated)
            analytic.save()
            # if threshold is reached, we exit the for loop
            if analytic.maxhosts_count >= ON_MAXHOSTS_REACHED['THRESHOLD']:
                break

        # Anomaly detection for hits_count (compute zscore against all snapshots available in DB)
        snapshots = Snapshot.objects.filter(analytic=analytic)
        a = np.array([c.hits_count for c in snapshots])
        z = stats.zscore(a)
        zscore_count = z[-1]
        if isnan(zscore_count):
            zscore_count = -9999
        if zscore_count > analytic.anomaly_threshold_count:
            anomaly_alert_count = True
        else:
            anomaly_alert_count = False
        
        # Anomaly detection for hits_endpoints (compute zscore against all snapshots available in DB)
        a = np.array([c.hits_endpoints for c in snapshots])
        z = stats.zscore(a)
        zscore_endpoints = z[-1]
        if isnan(zscore_endpoints):
            zscore_endpoints = -9999
        if zscore_endpoints > analytic.anomaly_threshold_endpoints:
            anomaly_alert_endpoints = True
        else:
            anomaly_alert_endpoints = False
        
        # Final update of snpashots with stats for the last snapshot (just created above)            
        snapshot.zscore_count = zscore_count
        snapshot.zscore_endpoints = zscore_endpoints
        snapshot.anomaly_alert_count = anomaly_alert_count
        snapshot.anomaly_alert_endpoints = anomaly_alert_endpoints
        snapshot.save()
        

        # Update Celery task progress
        celery_status.progress = (DB_DATA_RETENTION-days)*100/DB_DATA_RETENTION
        celery_status.save()

    # Close Campaign
    campaign.date_end = datetime.now()
    campaign.save()

    # Delete Celery task in DB
    celery_status.delete()


@shared_task()
def regenerate_campaign(campaigndate):
    # We assume that the task is managed by Celery because it is called from the tasks.py file
    run_campaign(campaigndate=campaigndate, celery=True)
