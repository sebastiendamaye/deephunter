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

def get_requirements():
    """
    Return the required modules for the connector.
    """
    init_globals()
    return ['requests']

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

def get_github_contents(repo):
    """
    Returns a list of JSON files in a GitHub repo
    :param repo: The repo object
    :return: A list of JSON files or empty list if error
    """
    init_globals()

    owner, repo_name, branch, path = parse_github_url(repo.url)
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{path}"
    
    if repo.token:
        headers = {
            "Authorization": f"token {repo.token}",
            "Accept": "application/vnd.github.v3+json"
        }
    else:
        headers = {}
    
    response = requests.get(api_url, headers=headers, proxies=PROXY)
    
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
    add_error_notification(f"GitHub connector: error (status code {response.status_code}) connecting to {repo.url}")
    return []
    