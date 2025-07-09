from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import Query

# Dynamically import all connectors
import importlib
import pkgutil
import plugins
all_connectors = {}
for loader, module_name, is_pkg in pkgutil.iter_modules(plugins.__path__):
    module = importlib.import_module(f"plugins.{module_name}")
    all_connectors[module_name] = module


PROXY = settings.PROXY

# This handler is triggered before a "Query" object is saved (pre_save when created or updated)
@receiver(pre_save, sender=Query)
def pre_save_handler(sender, instance, **kwargs):
    
    # Check if the instance is being updated (i.e., it's not a new object)
    if instance.pk:
        # Retrieve the current value of the field from the database
        original_instance = Query.objects.get(pk=instance.pk)

        ### Reset counters and error flag when the "query" field of the analytic is updated
        if original_instance.query != instance.query:
            # reset query flag
            instance.maxhosts_count = 0
            instance.query_error = False
            instance.query_error_message = ''

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


"""
# This handler is triggered after a "Query" object is saved (created or updated)
@receiver(post_save, sender=Query)
def post_save_handler(sender, instance, created, **kwargs):

    # Only apply if "need_to_sync_rule" function returns True (defined in the connector settings)
    if all_connectors.get(instance.connector.name).need_to_sync_rule():

        # only apply if create_rule flag set
        if instance.create_rule:

            # For "newly" created analytic
            if created:
                # call the "create_rule" function of the connector
                all_connectors.get(instance.connector.name).create_rule(instance)
                    
            # When analytic is updated
            else:
                # call the "update_rule" function of the connector
                all_connectors.get(instance.connector.name).update_rule(instance)
"""

# This handler is triggered after a "Query" object is deleted
@receiver(post_delete, sender=Query)
def post_delete_handler(sender, instance, **kwargs):

    # Only apply if "need_to_sync_rule" function returns True, for the connector of the analytic
    if all_connectors.get(instance.connector.name).need_to_sync_rule():
        
        # only apply if create_rule flag set
        if instance.create_rule:
            # call the "delete_rule" function of the connector
            all_connectors.get(instance.connector.name).delete_rule(instance)
