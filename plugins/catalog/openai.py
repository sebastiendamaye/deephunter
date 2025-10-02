"""
OpenAI (ChatGPT) plugin for DeepHunter

Requirements
------------
- pip install openai
- Get an API key: https://platform.openai.com/account/api-keys

Description
-----------
This plugin integrates OpenAI's ChatGPT to suggest MITRE techniques based on a given query.
"""

from openai import OpenAI
from django.conf import settings
from connectors.utils import get_connector_conf
import re

_globals_initialized = False
def init_globals():
    global DEBUG, PROXY, API_KEY, MODEL
    global _globals_initialized
    if not _globals_initialized:
        DEBUG = False
        PROXY = settings.PROXY
        API_KEY = get_connector_conf('openai', 'API_KEY')
        MODEL = get_connector_conf('openai', 'MODEL')
        _globals_initialized = True


def get_requirements():
    """
    Return the required modules for the connector.
    """
    init_globals()
    return ['openai']

def get_mitre_techniques_from_query(query):
    init_globals()

    client = OpenAI(api_key=API_KEY)

    prompt = f"""
    List only the MITRE ATT&CK TTP IDs (e.g., T1059, T1021.002) that match this query. No descriptions, no explanation.

    Query:
    {query}
    """

    response = client.responses.create(
        model=MODEL,
        input=prompt
    )

    mitre_ttps = re.findall(r'T\d{4}(?:\.\d{3})?', response.output_text)
    return list(set(mitre_ttps))

def write_query_with_ai(prompt):
    init_globals()

    client = OpenAI(api_key=API_KEY)

    response = client.responses.create(
        model=MODEL,
        input=prompt
    )

    return response.output_text
