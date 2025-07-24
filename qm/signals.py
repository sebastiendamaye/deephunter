from django.db.models.signals import pre_save, post_save, post_delete
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from .models import Analytic, TasksStatus
from qm.utils import token_expiration_check, is_update_available
from qm.tasks import regenerate_stats
import time

# Dynamically import all connectors
import importlib
import pkgutil
import plugins
all_connectors = {}
for loader, module_name, is_pkg in pkgutil.iter_modules(plugins.__path__):
    module = importlib.import_module(f"plugins.{module_name}")
    all_connectors[module_name] = module

PROXY = settings.PROXY
DAYS_BEFORE_REVIEW = settings.DAYS_BEFORE_REVIEW
AUTO_STATS_REGENERATION = settings.AUTO_STATS_REGENERATION

# This function is called after a user logs in
@receiver(user_logged_in)
def user_logged_in_receiver(sender, request, user, **kwargs):
    request.session['update_available'] = is_update_available()
    request.session['tokenexpires'] = token_expiration_check()

# This function is already defined in the views, but expects the request param that is not available in the signal handler.
# So we cloned this function here so that it can be called from the signal handler.
def regenerate_analytic_stats(analytic):
    # sleep 1 second to make sure the task is not started immediately
    # unless we do that, the task fails for newly created analytics
    time.sleep(1)

    # start the celery task (defined in qm/tasks.py)
    taskid = regenerate_stats.delay(analytic.id)
    
    # Create task in TasksStatus object
    celery_status = TasksStatus(
        taskname=analytic.name,
        taskid = taskid
    )
    celery_status.save()

# This handler is triggered before an "Analytic" object is saved (pre_save when created or updated)
@receiver(pre_save, sender=Analytic)
def pre_save_handler(sender, instance, **kwargs):
    
    # Check if the instance is being updated (i.e., it's not a new object)
    if instance.pk:
        # Retrieve the current value of the field from the database
        original_instance = Analytic.objects.get(pk=instance.pk)

        ### Reset counters and error flag when the "query" field of the analytic is updated
        if original_instance.query != instance.query:
            # reset query flag
            instance.maxhosts_count = 0
            instance.query_error = False
            instance.query_error_message = ''
            # we save a flag for the post_save handler to know if the query was changed
            instance._query_changed = True

        # Only apply if "need_to_sync_rule" function returns True (defined in the connector settings)
        if all_connectors.get(instance.connector.name).need_to_sync_rule():

            # If create_rule flag was initially set
            if original_instance.create_rule:
                if instance.create_rule:
                    if original_instance.query != instance.query:
                        all_connectors.get(instance.connector.name).update_rule(instance)
                else:
                    all_connectors.get(instance.connector.name).delete_rule(instance)
            
            else:
                # if the updated analytic has the create_rule flag set while it was not set before,
                # we need to create the remote rule associated with the analytic
                if instance.create_rule:
                    all_connectors.get(instance.connector.name).create_rule(instance)


    # For "newly" created analytic
    else:
        
        # Only apply if "need_to_sync_rule" function returns True (defined in the connector settings)
        if all_connectors.get(instance.connector.name).need_to_sync_rule():
            # if the create_rule flag is set, we need to create the remote rule associated with the analytic
            if instance.create_rule:
                all_connectors.get(instance.connector.name).create_rule(instance)

    # Workflow. Set the next review date if the analytic is published
    if instance.status == 'PUB':
        if not instance.run_daily_lock:
            instance.next_review_date = datetime.now().date() + timedelta(days=DAYS_BEFORE_REVIEW)
        else:
            instance.next_review_date = None

    # When analytics are archived, automatically remove the run_daily flag
    if instance.status == 'ARCH' or instance.status == 'PENDING':
        instance.run_daily = False


# This handler is triggered after an "Analytic" object is saved
@receiver(post_save, sender=Analytic)
def post_save_handler(sender, instance, created, **kwargs):

    if created:
        # New analytics
        if AUTO_STATS_REGENERATION:
            regenerate_analytic_stats(instance)
    else:
        # for updated analytics, we check the flag set by the pre_save handler
        if getattr(instance, '_query_changed', False):
            if AUTO_STATS_REGENERATION:
                regenerate_analytic_stats(instance)


# This handler is triggered after an "Analytic" object is deleted
@receiver(post_delete, sender=Analytic)
def post_delete_handler(sender, instance, **kwargs):

    # Only apply if "need_to_sync_rule" function returns True, for the connector of the analytic
    if all_connectors.get(instance.connector.name).need_to_sync_rule():
        
        # only apply if create_rule flag set
        if instance.create_rule:
            # call the "delete_rule" function of the connector
            all_connectors.get(instance.connector.name).delete_rule(instance)
