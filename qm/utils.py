from django.conf import settings
from datetime import datetime, timedelta, timezone
from qm.models import Campaign, Analytic, Snapshot, Endpoint, TasksStatus
from django.shortcuts import get_object_or_404
import numpy as np
from scipy import stats
from math import isnan
import requests
from notifications.utils import add_info_notification, add_success_notification, add_warning_notification, del_notification_by_uid

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


def is_mitre_update_available():
    """
    Check if a new version of the MITRE ATT&CK framework is available.
    The check is done by comparing the local version with the remote version.
    Returns bool: True if an update is available, False otherwise.
    """

    try:
        r = requests.get(
            'https://api.github.com/repos/mitre-attack/attack-stix-data/releases/latest',
            proxies=PROXY
        )
        remote_version_mitre = r.json()['tag_name']

        # local version MITRE
        with open(f'{STATIC_PATH}/VERSION_MITRE', 'r') as f:
            local_version_mitre = f.readline().strip()
        
        # compare
        if local_version_mitre != remote_version_mitre:
            return True
        else:
            return False
            
    except:
        return False

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

    add_info_notification(f"Running campaign for date: {campaigndate.strftime('%Y-%m-%d')}")
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
        analytic.query_error_date = None
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

        # if error, we exit the for loop
        if data == "ERROR":
            break

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
            
            # there are results, we can update the last_time_seen field of the analytic
            analytic.last_time_seen = snapshot.date
            analytic.save()

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
            # Send notification
            del_notification_by_uid(f"max_number_hosts_reached_{datetime.now().strftime('%Y%m%d')}_{analytic.id}")
            add_info_notification(f"Max number of hosts reached for analytic {analytic.name}", uid=f"max_number_hosts_reached_{datetime.now().strftime('%Y%m%d')}_{analytic.id}")
            # Update the maxhost counter if reached
            analytic.maxhosts_count += 1
            # if threshold is reached
            if analytic.maxhosts_count >= ON_MAXHOSTS_REACHED['THRESHOLD']:
                # notification
                add_warning_notification(f"Max hosts threshold reached for analytic {analytic.name}")
                # If DISABLE_RUN_DAILY is set and run_daily_lock is not set, we disable the run_daily flag for the analytic
                if ON_MAXHOSTS_REACHED['DISABLE_RUN_DAILY'] and not analytic.run_daily_lock:
                    analytic.run_daily = False
                    analytic.status = 'PENDING'
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
    campaign.nb_queries = Analytic.objects.exclude(status='ARCH').filter(run_daily=True).count()
    campaign.nb_analytics = Analytic.objects.exclude(status='ARCH').count()
    campaign.save()

    # Delete Celery task in DB if celery is used
    task_status.delete()

    add_success_notification(f"Campaign for date {campaigndate.strftime('%Y-%m-%d')} complete")


def get_available_statuses(analytic, edit=False):
    statuses = {}
    if analytic.status == "DRAFT":
        if not edit:
            statuses = {
                "PUB_RUNDAILY": "Publish (run daily set)",
                "PUB_NO_RUNDAILY": "Publish (run daily unset)",
                "ARCH": "Archive",
                }
        else:
            statuses = {
                "DRAFT": "Draft",
                "PUB": "Publish",
                "ARCH": "Archive",
                }
    elif analytic.status == "PUB":
        # if analytic is locked, it's protected against review
        if analytic.run_daily_lock:
            if not edit:
                statuses = {
                    "PENDING": "Pending Update",
                    "ARCH": "Archive",
                    }
            else:
                statuses = {
                    "PUB": "Publish",
                    "PENDING": "Pending Update",
                    "ARCH": "Archive",
                    }
        else:
            if not edit:
                statuses = {
                    "PENDING": "Pending Update",
                    "REVIEW": "To review",
                    "ARCH": "Archive",
                    }
            else:
                statuses = {
                    "PUB": "Publish",
                    "PENDING": "Pending Update",
                    "REVIEW": "To review",
                    "ARCH": "Archive",
                    }
    elif analytic.status == "REVIEW":
        if not edit:
            statuses = {}
        else:
            statuses = {
                "REVIEW": "To review",
                }
    elif analytic.status == "PENDING":
        if not edit:
            statuses = {
                "DRAFT": "Draft",
                "ARCH": "Archive",
                }
        else:
            statuses = {
                "DRAFT": "Draft",
                "PENDING": "Pending Update",
                "ARCH": "Archive",
                }

    elif analytic.status == "ARCH":
        if not edit:
            statuses = {
                "DRAFT": "Draft",
                "PUB_RUNDAILY": "Publish (run daily set)",
                "PUB_NO_RUNDAILY": "Publish (run daily unset)",
                "REVIEW": "To review",
                }
        else:
            statuses = {
                "DRAFT": "Draft",
                "PUB": "Publish",
                "REVIEW": "To review",
                "ARCH": "Archive",
                }
    
    return statuses

def find_sha_by_parent_sha(parent_sha, branch='main', per_page=100):
    url = f'https://api.github.com/repos/sebastiendamaye/deephunter/commits'
    params = {'sha': branch, 'per_page': per_page}
    response = requests.get(
        url,
        params=params,
        proxies=PROXY
    )
    if response.status_code != 200:
        raise Exception(f"Failed to fetch commits: {response.status_code}")
    commits = response.json()
    for commit in commits:
        parents = commit.get('parents', [])
        if any(p['sha'] == parent_sha for p in parents):
            return commit['sha']
    return None
