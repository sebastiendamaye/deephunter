from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from .forms import ConnectorConfFormSet
from connectors.models import Connector, ConnectorConf
from django.contrib.auth.decorators import login_required, permission_required

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
        return HttpResponseRedirect('/config/deephunter-settings/')
    
    else:
        formset = ConnectorConfFormSet(queryset=qs)

    return render(request, "selected_connector_settings.html", {
        "formset": formset,
        "connector": connector,
    })