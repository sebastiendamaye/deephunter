from django.shortcuts import render, HttpResponse
from .forms import ConnectorSelectForm, ConnectorConfFormSet
from connectors.models import Connector, ConnectorConf

def connector_conf(request):
    formset = None
    connector = None

    if request.method == "POST":
        # Try to get connector from POST (hidden field in formset form)
        connector_id = request.POST.get('connector')
        connector = None
        if connector_id:
            connector = Connector.objects.get(pk=connector_id)
        form = ConnectorSelectForm(request.POST)
        if connector:
            qs = ConnectorConf.objects.filter(connector=connector)
            if 'save_changes' in request.POST:
                formset = ConnectorConfFormSet(request.POST, queryset=qs)
                if formset.is_valid():
                    formset.save()
            else:
                formset = ConnectorConfFormSet(queryset=qs)
        else:
            formset = None
    
    else:
        form = ConnectorSelectForm()
        if 'connector' in request.GET:
            connector = request.GET.get('connector')
            qs = ConnectorConf.objects.filter(connector=connector)
            formset = ConnectorConfFormSet(queryset=qs)

    return render(request, "connector_conf.html", {
        "form": form,
        "formset": formset,
        "connector": connector,
    })