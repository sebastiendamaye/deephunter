from django.conf import settings
from datetime import datetime, timedelta
import numpy as np
from scipy import stats
from math import isnan
from qm.models import Query, Snapshot, Campaign, Endpoint, CeleryStatus
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
def regenerate_stats(query_id):
    query = get_object_or_404(Query, pk=query_id)

    # we assume that query won't fail (flag will be set later if query fails)
    query.query_error = False
    query.query_error_message = ''
    query.save()
    
    # Create Campaign
    # Date of campaign is when the script runs (today) while snapshot date is the day before (detection date)
    campaign = Campaign(
        name='regenerate_stats_{}_{}'.format(query.name, datetime.now().strftime("%Y-%m-%d-%H-%M")),
        description='Regenerate stats for {}'.format(query.name),
        date_start=datetime.now(),
        nb_queries=1
        )
    campaign.save()

    # Create task in CeleryStatus object
    celery_status = CeleryStatus(
        query=query,
        progress=0
        )
    celery_status.save()
    
    # Delete all snapshots for this query
    # (related Endpoint object will automatically cascade delete)
    Snapshot.objects.filter(query=query).delete()
    
    # Rebuild campaigns for last DB_DATA_RETENTION (90 days by default) for the query
    for days in reversed(range(DB_DATA_RETENTION)):
        
        # store current time (used to update snapshot runtime)
        start_runtime = datetime.now()

        # Call the "query" function of the appropriate connector
        # (no date range provided, so it will use the last 24 hours by default)
        todate = datetime.combine((datetime.now() - timedelta(days=days)), datetime.min.time())
        fromdate = (todate - timedelta(days=1))
        data = all_connectors.get(query.connector.name).query(query, fromdate.isoformat(), todate.isoformat())

        # store current time (used to update snapshot runtime)
        end_runtime = datetime.now()

        # Create snapshot. Necessary to have the object to link the detected assets.
        # Stats will be updated later to the snaptshot
        # the date of the snapshot is the day before the campaign (detection date)
        snapshot = Snapshot(
            campaign=campaign,
            query=query,
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
            query.maxhosts_count += 1
            # if threshold is reached
            if query.maxhosts_count >= ON_MAXHOSTS_REACHED['THRESHOLD']:
                # If DISABLE_RUN_DAILY is set and run_daily_lock is not set, we disable the run_daily flag for the query
                if ON_MAXHOSTS_REACHED['DISABLE_RUN_DAILY'] and not query.run_daily_lock:
                    query.run_daily = False
                # If DELETE_STATS is set and run_daily_lock is not set, we delete all stats for the query
                if ON_MAXHOSTS_REACHED['DELETE_STATS'] and not query.run_daily_lock:
                    Snapshot.objects.filter(query=query).delete()
            # we update the query (counter updated, and flags updated)
            query.save()
            # if threshold is reached, we exit the for loop
            if query.maxhosts_count >= ON_MAXHOSTS_REACHED['THRESHOLD']:
                break

        # Anomaly detection for hits_count (compute zscore against all snapshots available in DB)
        snapshots = Snapshot.objects.filter(query = query)
        a = np.array([c.hits_count for c in snapshots])
        z = stats.zscore(a)
        zscore_count = z[-1]
        if isnan(zscore_count):
            zscore_count = -9999
        if zscore_count > query.anomaly_threshold_count:
            anomaly_alert_count = True
        else:
            anomaly_alert_count = False
        
        # Anomaly detection for hits_endpoints (compute zscore against all snapshots available in DB)
        a = np.array([c.hits_endpoints for c in snapshots])
        z = stats.zscore(a)
        zscore_endpoints = z[-1]
        if isnan(zscore_endpoints):
            zscore_endpoints = -9999
        if zscore_endpoints > query.anomaly_threshold_endpoints:
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

    # Delete Celery task
    celery_status.delete()
