from django.conf import settings
from django.db import transaction, DatabaseError
from django.utils import timezone
from datetime import datetime, timedelta
from uuid import uuid4
import numpy as np
from scipy import stats
from math import isnan
from qm.models import Analytic, Snapshot, Campaign, Endpoint, TasksStatus
from connectors.models import Connector
from qm.utils import run_campaign, get_campaign_date
import requests
from celery import shared_task, current_app
from django.shortcuts import get_object_or_404
from time import sleep
from notifications.utils import add_info_notification, add_success_notification, add_warning_notification, add_error_notification, del_notification_by_uid

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

def start_regenerate_stats(analytic, started_by=None):
    """
    Start a stats regeneration for an analytic, cancelling any regeneration
    already running for it (e.g. when the analytic is modified mid-run).

    The TasksStatus row is reused and pointed at the new task id, generated
    upfront so that the row exists before the task starts. A cancelled task that
    keeps running (revoke is asynchronous) notices that the row no longer
    carries its id, and stops (see regenerate_stats).

    The existing stats of the analytic are deleted right away, so that the
    regeneration starts from a pristine state and the trend graph never shows a
    mix of old and recomputed stats.
    """
    taskid = str(uuid4())
    with transaction.atomic():
        current = TasksStatus.objects.select_for_update().filter(taskname=analytic.name).first()
        if current and current.taskid:
            # without signal='SIGKILL', the task is not cancelled immediately
            current_app.control.revoke(current.taskid, terminate=True, signal='SIGKILL')
        TasksStatus.objects.update_or_create(
            taskname=analytic.name,
            defaults={
                'taskid': taskid,
                'progress': 0,
                'started_by': started_by,
                'date': timezone.now(),
            },
        )

    # Delete all snapshots for this analytic (related Endpoint objects are cascade
    # deleted). Done outside of the above transaction: a cancelled task that is
    # not killed yet may still be writing snapshots, and a DB conflict here must
    # not prevent the new regeneration from starting (the task deletes the
    # snapshots again when it starts anyway).
    try:
        with transaction.atomic():
            Snapshot.objects.filter(analytic=analytic).delete()
    except DatabaseError as e:
        add_warning_notification(f'Could not delete stats of analytic "{analytic.name}" before regenerating them: {e}')

    # Only start the task once the analytic and the TasksStatus row are
    # committed (if the transaction is rolled back, the task is never started).
    transaction.on_commit(lambda: regenerate_stats.apply_async((analytic.id,), task_id=taskid))
    return taskid

@shared_task(bind=True)
def regenerate_stats(self, analytic_id):
    # The TasksStatus row is looked up by task id (not by analytic name), so that
    # it is still found if the analytic is renamed while the task is running.
    # If it does not exist (anymore), this task has been cancelled or superseded
    # by a newer regeneration for the same analytic.
    celery_status = TasksStatus.objects.filter(taskid=self.request.id)
    if not celery_status.exists():
        return

    # Filled in by _regenerate_stats() once the campaign is created
    ctx = {}
    try:
        _regenerate_stats(self.request.id, celery_status, analytic_id, ctx)
    except Exception as e:
        # Never leave the TasksStatus row behind on failure: the UI would show the
        # task stalled at its last progress forever, and get_analytic_status
        # would report it as running.
        celery_status.delete()
        if ctx.get('campaign') is not None:
            # Discard the partial stats (cascade deleted with the campaign)
            ctx['campaign'].delete()
        add_error_notification(f'Regenerate stats task for analytic id {analytic_id} failed: {e}')
        raise

def _regenerate_stats(taskid, celery_status, analytic_id, ctx):
    analytic = get_object_or_404(Analytic, pk=analytic_id)

    add_info_notification(f'Regenerate stats task started for analytic "{analytic.name}"')

    # we assume that analytic won't fail (flag will be set later if analytic fails).
    analytic.analyticmeta.query_error = False
    analytic.analyticmeta.query_error_message = ''
    analytic.analyticmeta.query_error_date = None
    analytic.analyticmeta.save()
    
    # Create Campaign
    # Date of campaign is when the script runs (today) while snapshot date is the day before (detection date)
    # The campaign name must be unique: it includes the seconds and part of the
    # task id, as a regeneration can now be restarted within the same minute.
    campaign = Campaign(
        name='regenerate_stats_{}_{}_{}'.format(analytic.name, datetime.now().strftime("%Y-%m-%d-%H-%M-%S"), taskid[:8]),
        description='Regenerate stats for {}'.format(analytic.name),
        date_start=datetime.now(),
        nb_queries=1
        )
    campaign.save()
    ctx['campaign'] = campaign

    # Delete all snapshots for this analytic
    # (related Endpoint object will automatically cascade delete).
    # Already done when the regeneration is triggered (start_regenerate_stats),
    # repeated here in case a cancelled task wrote snapshots in the meantime.
    Snapshot.objects.filter(analytic=analytic).delete()
    
    # Rebuild campaigns for last DB_DATA_RETENTION (90 days by default) for the analytic
    for days in reversed(range(DB_DATA_RETENTION)):

        # Stop if the task has been cancelled or superseded (see start_regenerate_stats)
        if not celery_status.exists():
            _abort_regenerate_stats(analytic, campaign)
            return

        # store current time (used to update snapshot runtime)
        start_runtime = datetime.now()

        # Call the "query" function of the appropriate connector
        # (no date range provided, so it will use the last 24 hours by default)
        todate = datetime.combine((datetime.now() - timedelta(days=days)), datetime.min.time())
        fromdate = (todate - timedelta(days=1))
        data = all_connectors.get(analytic.connector.name).query(analytic, fromdate.isoformat(), todate.isoformat())

        # if error, we exit the for loop
        if data == "ERROR":
            break

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

            # there are results, we can update the last_time_seen field of the analytic
            analytic.analyticmeta.last_time_seen = snapshot.date
            analytic.analyticmeta.save()

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
            # Send notification
            del_notification_by_uid(f"max_number_hosts_reached_{datetime.now().strftime('%Y%m%d')}_{analytic.id}")
            add_info_notification(f"Max number of hosts reached for analytic {analytic.name}", uid=f"max_number_hosts_reached_{datetime.now().strftime('%Y%m%d')}_{analytic.id}")
            # Update the maxhost counter if reached
            analytic.analyticmeta.maxhosts_count += 1
            analytic.analyticmeta.save()
            # if threshold is reached
            if analytic.analyticmeta.maxhosts_count >= ON_MAXHOSTS_REACHED['THRESHOLD']:
                # notification
                add_warning_notification(f"Max hosts threshold reached for analytic {analytic.name}")
                # A superseded task must not update the (newer version of the) analytic
                if not celery_status.exists():
                    _abort_regenerate_stats(analytic, campaign)
                    return
                # Reload the analytic before updating it: it may have been edited
                # while this task was running, and saving the stale copy would
                # revert that edit (and trigger yet another stats regeneration).
                analytic.refresh_from_db()
                # If DISABLE_RUN_DAILY is set and run_daily_lock is not set, we disable the run_daily flag for the analytic
                if ON_MAXHOSTS_REACHED['DISABLE_RUN_DAILY'] and not analytic.run_daily_lock:
                    analytic.run_daily = False
                    analytic.status = 'PENDING'
                # If DELETE_STATS is set and run_daily_lock is not set, we delete all stats for the analytic
                if ON_MAXHOSTS_REACHED['DELETE_STATS'] and not analytic.run_daily_lock:
                    Snapshot.objects.filter(analytic=analytic).delete()
                # we update the analytic (flags updated)
                analytic.save()
            # if threshold is reached, we exit the for loop
            if analytic.analyticmeta.maxhosts_count >= ON_MAXHOSTS_REACHED['THRESHOLD']:
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
        

        # Update Celery task progress. update() (rather than save()) never
        # re-creates the row if it was deleted, i.e. if the task was cancelled.
        if not celery_status.update(progress=(DB_DATA_RETENTION-days)*100/DB_DATA_RETENTION):
            _abort_regenerate_stats(analytic, campaign)
            return

    # Close Campaign
    campaign.date_end = datetime.now()
    campaign.save()

    # Delete Celery task in DB (only this task's row, never a newer task's one)
    celery_status.delete()

    add_success_notification(f'Regenerate stats task for analytic "{analytic.name}" successfully completed.')

def _abort_regenerate_stats(analytic, campaign):
    """
    Clean up after a cancelled/superseded regenerate_stats task: delete the
    snapshots it created (identified by its own campaign, so the snapshots of a
    newer regeneration are left untouched) and the campaign itself.
    """
    # Snapshots (and their endpoints) are cascade-deleted with the campaign
    campaign.delete()
    add_info_notification(f'Regenerate stats task for analytic "{analytic.name}" cancelled.')

@shared_task()
def regenerate_campaign(campaigndate):
    # We assume that the task is managed by Celery because it is called from the tasks.py file
    run_campaign(campaigndate=campaigndate, celery=True)
