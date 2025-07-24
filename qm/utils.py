from django.conf import settings
from datetime import datetime, timedelta, timezone
from qm.models import Campaign, Analytic, Snapshot, Endpoint, TasksStatus
from django.shortcuts import get_object_or_404
import numpy as np
from scipy import stats
from math import isnan
import requests
from connectors.utils import is_connector_enabled

# Dynamically import all connectors
import importlib
import pkgutil
import plugins
all_connectors = {}
for loader, module_name, is_pkg in pkgutil.iter_modules(plugins.__path__):
    module = importlib.import_module(f"plugins.{module_name}")
    all_connectors[module_name] = module

PROXY = settings.PROXY
STATIC_PATH = settings.STATIC_ROOT
BASE_DIR = settings.BASE_DIR
UPDATE_ON = settings.UPDATE_ON
DB_DATA_RETENTION = settings.DB_DATA_RETENTION
GITHUB_LATEST_RELEASE_URL = settings.GITHUB_LATEST_RELEASE_URL
GITHUB_COMMIT_URL = settings.GITHUB_COMMIT_URL
CAMPAIGN_MAX_HOSTS_THRESHOLD = settings.CAMPAIGN_MAX_HOSTS_THRESHOLD
ON_MAXHOSTS_REACHED = settings.ON_MAXHOSTS_REACHED
DISABLE_RUN_DAILY_ON_ERROR = settings.DISABLE_RUN_DAILY_ON_ERROR


def is_update_available():
    """
    Check if a new version of the application is available.
    The check is done by comparing the local version with the remote version, either based on commits or releases.
    Returns bool: True if an update is available, False otherwise.
    """
    try:
        
        # update on new release only
        if UPDATE_ON == 'release':
            r = requests.get(
                GITHUB_LATEST_RELEASE_URL,
                proxies=PROXY
                )
            remote_ver = r.json()['name']
            # local version
            with open(f'{STATIC_PATH}/VERSION', 'r') as f:
                local_ver = f.readline().strip()
        else:
            # update on every new commit
            r = requests.get(
                GITHUB_COMMIT_URL,
                proxies=PROXY
                )
            remote_ver = r.text.strip()
            # local version
            with open(f'{STATIC_PATH}/commit_id.txt', 'r') as f:
                local_ver = f.readline().strip()
            
        # compare
        if local_ver != remote_ver:
            return True
        else:
            return False
            
    except:
        return False

def token_expiration_check():
    # Check if token is about to expire
    tokenexpires = 999
    if is_connector_enabled('sentinelone'):
        expires_on = all_connectors.get('sentinelone').get_token_expiration_date()
        if expires_on:
            dt = datetime.strptime(expires_on, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = dt - now
            tokenexpires = delta.days + 1    
    
    return tokenexpires

def get_campaign_date(campaign):
    """
    Helper function to get the campaign date from the campaign name.
    The campaign name is expected to be in the format 'daily_cron_YYYY-MM-DD'.
    """
    return datetime.strptime(campaign.name.replace('daily_cron_', ''), "%Y-%m-%d").date()

def run_campaign(campaigndate=None, debug=False, celery=False):

    if not campaigndate:
        # If no date provided, use today
        campaigndate = datetime.now()
    
    campaign_name = 'daily_cron_{}'.format(campaigndate.strftime("%Y-%m-%d"))

    if celery:
        # if task is managed by Celery, no need to create a new TasksStatus object as it is already created
        task_status = get_object_or_404(TasksStatus, taskname=campaign_name)
    else:
        # if task is started by cron, we create a new TasksStatus object
        task_status = TasksStatus(taskname=campaign_name)
        task_status.save()


    # Define the range (day-1@midnight to day@midnight)
    from_date = datetime.combine(campaigndate - timedelta(days=1), datetime.min.time())
    to_date = datetime.combine(campaigndate, datetime.min.time())

    # Create Campaign
    campaign = Campaign(
        name=campaign_name,
        description='Daily cron job, run all analytics',
        date_start=datetime.now()
        )
    campaign.save()
    
    # List of analytics with the run_daily flag but not archived
    analytics = Analytic.objects.filter(run_daily=True).exclude(status='ARCH')

    # Filter analytic with the "run_daily" flag set
    for progress, analytic in enumerate(analytics, start=1):
        
        # we assume that analytic won't fail (flag will be set later if analytic fails)
        analytic.query_error = False
        analytic.query_error_message = ''
        analytic.save()
                
        # store current time (used to update snapshot runtime)
        start_runtime = datetime.now()
        
        # Call the "query" function of the appropriate connector
        # Number of endpoints is evaluated by length of data. The data arrary returned should have the following fields:
        #  - endpoint name
        #  - site name (endpoint name group)
        #  - number of events
        #  - storylineIDs separated by commas
        data = all_connectors.get(analytic.connector.name).query(
            analytic=analytic,
            from_date=from_date.isoformat(),
            to_date=to_date.isoformat(),
            debug=debug
            )
        
        # store current time (used to update snapshot runtime)
        end_runtime = datetime.now()

        # Create snapshot. Necessary to have the object to link the detected assets.
        # Stats will be updated later to the snapshot
        # the date of the snapshot is the day before the campaign (detection date)
        snapshot = Snapshot(
            campaign=campaign,
            analytic=analytic,
            date=campaigndate-timedelta(days=1),
            runtime = (end_runtime-start_runtime).total_seconds()
            )
        snapshot.save()
                
        if debug:
            print(f'***DATA: {data}')
        
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
            if debug:
                print('NO DATA!')
            hits_count = 0
            hits_endpoints = 0
        
        if debug:
            print(f"*** HITS_COUNT = {hits_count}")
            print(f"*** HITS_ENDPOINTS = {hits_endpoints}")
        
        # Now that stats have been collected, snapshot is updated.
        snapshot.hits_count = hits_count
        snapshot.hits_endpoints = hits_endpoints
        snapshot.save()
        if debug:
            print("Snapshot created")
        
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
            if debug:
                print("Max hosts threshold reached. Counter updated")            
        
        # Anomaly detection for hits_count (compute zscore against all snapshots available in DB)
        if debug:
            print("Anomaly detection for hits_count")
        snapshots = Snapshot.objects.filter(analytic=analytic)
        a = np.array([c.hits_count for c in snapshots])
        z = stats.zscore(a)
        if debug:
            for i,v in enumerate(a):
                print( '{},{}'.format(v,z[i]) )
        zscore_count = z[-1]
        if isnan(zscore_count):
            zscore_count = -9999
        if zscore_count > analytic.anomaly_threshold_count:
            anomaly_alert_count = True
        else:
            anomaly_alert_count = False
        
        # Anomaly detection for hits_endpoints (compute zscore against all snapshots available in DB)
        if debug:
            print("Anomaly detection for hits_endpoints")
        a = np.array([c.hits_endpoints for c in snapshots])
        z = stats.zscore(a)
        if debug:
            for i,v in enumerate(a):
                print( '{},{}'.format(v,z[i]) )
        zscore_endpoints = z[-1]
        if isnan(zscore_endpoints):
            zscore_endpoints = -9999
        if zscore_endpoints > analytic.anomaly_threshold_endpoints:
            anomaly_alert_endpoints = True
        else:
            anomaly_alert_endpoints = False
        
        # Final update of snapshots with stats for the last snapshot (just created above)
        if debug:
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
        
        # update task progress
        task_status.progress = progress / analytics.count() * 100
        task_status.save()

        if debug:
            print(f"PROGRESS: {progress / analytics.count() * 100}%")
            print("================================")


    # Close Campaign
    campaign.date_end = datetime.now()
    campaign.nb_queries = Analytic.objects.filter(run_daily=True).count()
    campaign.save()

    # Delete Celery task in DB if celery is used
    task_status.delete()
