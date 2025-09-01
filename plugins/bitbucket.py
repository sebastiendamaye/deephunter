"""
Bitbucket connector
Used for repo sync with Bitbucket
"""

from urllib.parse import urlparse
import requests
from django.conf import settings
from pathlib import Path
from notifications.utils import add_error_notification
from requests.auth import HTTPBasicAuth

_globals_initialized = False
def init_globals():
    global DEBUG, PROXY
    global _globals_initialized
    if not _globals_initialized:
        DEBUG = False
        PROXY = settings.PROXY
        _globals_initialized = True

def parse_bitbucket_url(url):
    init_globals()

    parsed = urlparse(url)
    parts = parsed.path.strip('/').split('/')
    repo_owner = parts[0]
    repo_slug = parts[1]
    branch = parts[3]
    path = parts[4] if len(parts) > 4 else ''
    return repo_owner, repo_slug, branch, path

def get_bitbucket_contents(repo):
    """
    Returns a list of JSON files in a Bitbucket repo
    :param repo: The repo object
    :return: A list of JSON files or empty list if error
    """
    init_globals()

    full = []
    repo_owner, repo_slug, branch, path = parse_bitbucket_url(repo.url)
    if path:
        api_url = f"https://api.bitbucket.org/2.0/repositories/{repo_owner}/{repo_slug}/src/{branch}/{path}"
    else:
        api_url = f"https://api.bitbucket.org/2.0/repositories/{repo_owner}/{repo_slug}/src/{branch}/"

    if repo.token:
        response = requests.get(api_url, auth=HTTPBasicAuth(repo_owner, repo.token), proxies=PROXY)
    else:
        response = requests.get(api_url, proxies=PROXY)
    
    if response.status_code == 200:
        data = response.json()
        for item in data.get('values'):
            if item['type'] == 'commit_file' and Path(item['path']).suffix == ".json":
                full.append({
                    "name": item['path'],
                    "download_url": item['links']['self']['href']
                })

        # Bitbucket is paginating results. The "next" key returns the URL of the next page results
        while "next" in response.json():
            api_url = response.json()["next"]
            if repo.token:
                response = requests.get(api_url, auth=HTTPBasicAuth(repo_owner, repo.token), proxies=PROXY)
            else:
                response = requests.get(api_url, proxies=PROXY)
            data = response.json()
            for item in data.get('values'):
                if item['type'] == 'commit_file' and Path(item['path']).suffix == ".json":
                    full.append({
                        "name": item['path'],
                        "download_url": item['links']['self']['href']
                    })

        return full

    # In case of an error
    add_error_notification(f"Bitbucket connector: error (status code {response.status_code}) connecting to {repo.url}")
    return []
