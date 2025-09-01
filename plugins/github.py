"""
GitHub connector
Used for repo sync with GitHub
"""

from urllib.parse import urlparse
import requests
from django.conf import settings
from pathlib import Path
from notifications.utils import add_error_notification

_globals_initialized = False
def init_globals():
    global DEBUG, PROXY
    global _globals_initialized
    if not _globals_initialized:
        DEBUG = False
        PROXY = settings.PROXY
        _globals_initialized = True

def parse_github_url(url):
    init_globals()

    parsed = urlparse(url)
    parts = parsed.path.strip('/').split('/')
    owner = parts[0]
    repo = parts[1]
    # Find if 'tree' is present and get the path after branch name
    if 'tree' in parts:
        tree_index = parts.index('tree')
        branch = parts[tree_index + 1]
        path = '/'.join(parts[tree_index + 2:])
    else:
        branch = None
        path = ''
    return owner, repo, branch, path

def get_github_contents(url):
    init_globals()

    owner, repo, branch, path = parse_github_url(url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    
    response = requests.get(api_url, proxies=PROXY)
    if response.status_code == 200:
        data = response.json()
        return [
            {
                "name": item['name'],
                "download_url": item['download_url']
            }
            for item in data
            if item['type'] == 'file' and Path(item['name']).suffix == ".json"
        ]

    # In case of an error
    add_error_notification(f"GitHub connector: error (status code {response.status_code}) connecting to {url}")
    return []
    