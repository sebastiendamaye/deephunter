from django.conf import settings
from datetime import datetime, timedelta
import numpy as np
from scipy import stats
from math import isnan
from qm.models import Query, Snapshot, Campaign, Endpoint
import logging

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

DEBUG = False

# Get an instance of a logger
logger = logging.getLogger(__name__)

def run():

    # Cleanup all campaigns older than DB_DATA_RETENTION (90 days by default). Will automatically cascade delete snapshots and endpoints
    # Date of campaign is when the script runs (today) while snapshot date is the day before (detection date)
    Campaign.objects.filter(date_start__lt=datetime.today()-timedelta(days=DB_DATA_RETENTION)).delete()
    # Make sure remaining old Snapshots/Endpoints are also deleted (when regen stats is used, campaign date is today, while 1st stats are 3 months old)
    Snapshot.objects.filter(date__lt=datetime.today()-timedelta(days=DB_DATA_RETENTION)).delete()

    # Create Campaign
    campaign = Campaign(
        name='daily_cron_{}'.format(datetime.now().strftime("%Y-%m-%d")),
        description='Daily cron job, run all analytics',
        date_start=datetime.now()
        )
    campaign.save()
    
    # Filter query with the "run_daily" flag set
    for query in Query.objects.filter(run_daily=True):
        
        # we assume that query won't fail (flag will be set later if query fails)
        query.query_error = False
        query.query_error_message = ''
        query.save()
                
        # store current time (used to update snapshot runtime)
        start_runtime = datetime.now()
        
        # Call the "query" function of the appropriate connector
        # (no date range provided, so it will use the last 24 hours by default)
        # Number of endpoints is evaluated by length of data. The data arrary returned should have the following fields:
        #  - endpoint name
        #  - site name (endpoint name group)
        #  - number of events
        #  - storylineIDs separated by commas
        data = all_connectors.get(query.connector.name).query(query, debug=DEBUG)
        
        # store current time (used to update snapshot runtime)
        end_runtime = datetime.now()

        # Create snapshot. Necessary to have the object to link the detected assets.
        # Stats will be updated later to the snapshot
        # the date of the snapshot is the day before the campaign (detection date)
        snapshot = Snapshot(
            campaign=campaign,
            query=query,
            date=datetime.now()-timedelta(days=1),
            runtime = (end_runtime-start_runtime).total_seconds()
            )
        snapshot.save()
                
        if DEBUG:
            print(f'***DATA: data')
        
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
            if DEBUG:
                print('NO DATA!')
            hits_count = 0
            hits_endpoints = 0
        
        if DEBUG:
            print("*** HITS_COUNT = {}".format(hits_count))
            print("*** HITS_ENDPOINTS = {}".format(hits_endpoints))
        
        # Now that stats have been collected, snapshot is updated.
        snapshot.hits_count = hits_count
        snapshot.hits_endpoints = hits_endpoints
        snapshot.save()
        if DEBUG:
            print("Snapshot created")
        
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
            if DEBUG:
                print("Max hosts threshold reached. Counter updated")            
        
        # Anomaly detection for hits_count (compute zscore against all snapshots available in DB)
        if DEBUG:
            print("Anomaly detection for hits_count")
        snapshots = Snapshot.objects.filter(query = query)
        a = np.array([c.hits_count for c in snapshots])
        z = stats.zscore(a)
        if DEBUG:
            for i,v in enumerate(a):
                print( '{},{}'.format(v,z[i]) )
        zscore_count = z[-1]
        if isnan(zscore_count):
            zscore_count = -9999
        if zscore_count > query.anomaly_threshold_count:
            anomaly_alert_count = True
        else:
            anomaly_alert_count = False
        
        # Anomaly detection for hits_endpoints (compute zscore against all snapshots available in DB)
        if DEBUG:
            print("Anomaly detection for hits_endpoints")
        a = np.array([c.hits_endpoints for c in snapshots])
        z = stats.zscore(a)
        if DEBUG:
            for i,v in enumerate(a):
                print( '{},{}'.format(v,z[i]) )
        zscore_endpoints = z[-1]
        if isnan(zscore_endpoints):
            zscore_endpoints = -9999
        if zscore_endpoints > query.anomaly_threshold_endpoints:
            anomaly_alert_endpoints = True
        else:
            anomaly_alert_endpoints = False
        
        # Final update of snapshots with stats for the last snapshot (just created above)
        if DEBUG:
            print("***Final update for new snapshot")
            print("snapshot.zscore_count = {}".format(zscore_count))
            print("snapshot.zscore_endpoints = {}".format(zscore_endpoints))
            print("snapshot.anomaly_alert_count = {}".format(anomaly_alert_count))
            print("snapshot.anomaly_alert_endpoints = {}".format(anomaly_alert_endpoints))
        
        snapshot.zscore_count = zscore_count
        snapshot.zscore_endpoints = zscore_endpoints
        snapshot.anomaly_alert_count = anomaly_alert_count
        snapshot.anomaly_alert_endpoints = anomaly_alert_endpoints
        snapshot.save()
        
            
        if DEBUG:
            print("================================")

    # Close Campaign
    campaign.date_end = datetime.now()
    campaign.nb_queries = Query.objects.filter(run_daily=True).count()
    campaign.save()
