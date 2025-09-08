from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from .forms import ConnectorConfFormSet
from connectors.models import Connector, ConnectorConf
from django.contrib.auth.decorators import login_required, permission_required
from config.utils import touch
from django.conf import settings
import os

BASE_DIR = settings.BASE_DIR

@login_required
@permission_required('user.is_superuser', raise_exception=True)
def connector_conf(request):
    context = { 'connectors': Connector.objects.all() }
    return render(request, "connector_conf.html", context)


@login_required
@permission_required('user.is_superuser', raise_exception=True)
def selected_connector_settings(request, connector_id):
    connector = get_object_or_404(Connector, pk=connector_id)
    qs = ConnectorConf.objects.filter(connector=connector)

    if request.method == "POST":
        formset = ConnectorConfFormSet(request.POST, queryset=qs)
        if formset.is_valid():
            formset.save()
            # Bug #233 - touch the WSGI script file to force mod_wsgi to reload Django
            # unless you do that, changes to the settings may not be applied
            touch(os.path.join(BASE_DIR, 'deephunter', 'wsgi.py'))
        return HttpResponseRedirect('/config/deephunter-settings/')
    
    else:
        formset = ConnectorConfFormSet(queryset=qs)

    return render(request, "selected_connector_settings.html", {
        "formset": formset,
        "connector": connector,
    })