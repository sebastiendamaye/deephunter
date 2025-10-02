from django.shortcuts import get_object_or_404
from django.conf import settings
import requests
from qm.models import Analytic

DEBUG = False

PROXY = settings.PROXY

# Splits a list into chunks of a given size
def split(list_a, chunk_size):
    for i in range(0, len(list_a), chunk_size):
        yield list_a[i:i + chunk_size]

def run():
    analytic = get_object_or_404(Analytic, name='vulnerable_driver_name_detected_loldriver')
    if analytic.run_daily:
        
        # Use verify=False because of untrusted SSL certificate error
        url = 'https://www.loldrivers.io/api/drivers.json'
        r = requests.get(url, verify=False, proxies=PROXY)

        l = []
        for i in r.json():
            # json file is not compliant. It uses FileName or Filename
            if 'FileName' in i['KnownVulnerableSamples'][0]:
                if i['KnownVulnerableSamples'][0]['FileName'].strip() != '':
                    l.append(i['KnownVulnerableSamples'][0]['FileName'])
            else:
                if i['KnownVulnerableSamples'][0]['Filename'].strip() != '':
                    l.append(i['KnownVulnerableSamples'][0]['Filename'])

        # distinct value
        l = list(set(l))

        # Build the query with chunks of 100 items max in each sub lists
        chunk_size = 100
        l_chunks = list(split(l, chunk_size))
        s1ql_list = []
        for s in l_chunks:
            s1ql_list.append("tgt.file.path contains:anycase ({})".format(', '.join(["'\\\\{}'".format(i) for i in s])))

        s1ql = '\n  or '.join(s1ql_list)

        # build query
        dynamic_query = """endpoint.os = 'windows'
        and event.type = 'Driver Load'
        and (
        {}
        )""".format(s1ql)

        analytic.query = dynamic_query
        analytic.save()
