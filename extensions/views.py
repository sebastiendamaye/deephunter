from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from connectors.utils import is_valid_sha256

# Dynamically import all connectors
import importlib
import pkgutil
import plugins
all_connectors = {}
for loader, module_name, is_pkg in pkgutil.iter_modules(plugins.__path__):
    module = importlib.import_module(f"plugins.{module_name}")
    all_connectors[module_name] = module


PROXY = settings.PROXY

@login_required
@permission_required('extensions.view_extensions', raise_exception=True)
def loldriverhashchecker(request):

    hashes = ''
    found_hashes = ''
    
    if request.method == "POST":
        lol_hashes = []
        found_hashes = []
        hashes = request.POST['hashes']
        
        lol_hashes = all_connectors.get('loldrivers').get_sha256_hashes()
        
        # search if any matching hash
        for hash in hashes.split('\r\n'):
            hash = hash.strip()
            if is_valid_sha256(hash):
                if hash in lol_hashes:
                    found_hashes.append(hash)
    
    context = {
        'hashes': hashes,
        'output': found_hashes
    }
    return render(request, 'loldriverhashchecker.html', context)

@login_required
@permission_required('extensions.view_extensions', raise_exception=True)
def whois(request):

    ip = ''
    whois = ''

    if request.method == "POST":
        ip = request.POST['ip']
        whois = all_connectors.get('whois').whois(ip)
    else:
        whois = 'Provide an IP address in the above form.'
        
    context = {
        'ip': ip,
        'output': whois
    }
    return render(request, 'whois.html', context)

@login_required
@permission_required('extensions.view_extensions', raise_exception=True)
def malwarebazaarhashchecker(request):

    hashes = ''
    output = ''
    
    if request.method == "POST":
        output = []
        hashes = request.POST['hashes']

        for hash in hashes.split('\r\n'):
            hash = hash.strip()
            r = all_connectors.get('malwarebazaar').check_hash(hash)
            if r:
                output.append({
                    'hash': hash,
                    'foundinmb': 'Y',
                    'signature': r['signature']
                })        
            else:
                output.append({
                    'hash': hash,
                    'foundinmb': 'N',
                    'signature': ''
                })
                        
    context = {
        'hashes': hashes,
        'output': output
    }
    return render(request, 'malwarebazaarhashchecker.html', context)

@login_required
@permission_required('extensions.view_extensions', raise_exception=True)
def vthashchecker(request):

    hashes = ''
    output = ''
    
    if request.method == "POST":
        output = []
        hashes = request.POST['hashes']

        for hash in hashes.split('\r\n'):
            hash = hash.strip()
            file = all_connectors.get('virustotal').check_hash(hash)
            if file:
                output.append({
                    'hash': hash,
                    'foundinvt': 'Y',
                    'malicious': file.last_analysis_stats['malicious'],
                    'suspicious': file.last_analysis_stats['suspicious']
                })        
            else:
                output.append({
                    'hash': hash,
                    'foundinvt': 'N',
                    'malicious': '',
                    'suspicious': ''
                })        
                        
    context = {
        'hashes': hashes,
        'output': output
    }
    return render(request, 'vthashchecker.html', context)

@login_required
@permission_required('extensions.view_extensions', raise_exception=True)
def vtipchecker(request):

    ips = []
    output = []
    
    if request.method == "POST":
        ips = request.POST['ips']

        for ip in ips.split('\r\n'):
            ip = ip.strip()            
            vt = {}
            response = all_connectors.get('virustotal').check_ip(ip)
            vt['ip'] = ip
            try:
                vt['malicious'] = response['attributes']['last_analysis_stats']['malicious']
                vt['suspicious'] = response['attributes']['last_analysis_stats']['suspicious']
                vt['whois'] = response['attributes']['whois']
            except:
                vt['malicious'] = 'N/A'
                vt['suspicious'] = 'N/A'
                vt['whois'] = 'N/A'

            output.append(vt)
                        
    context = {
        'ips': ips,
        'output': output
    }
    return render(request, 'vtipchecker.html', context)
