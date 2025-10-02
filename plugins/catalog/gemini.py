"""
Gemini AI plugin for DeepHunter

Requirements
------------
- pip install google-genai
- Get an API key: https://aistudio.google.com/app/apikey

Description
-----------
This plugin integrates Google's Gemini AI to suggest MITRE techniques based on a given query.
"""

from google import genai
from google.genai.types import GenerateContentConfig
from django.conf import settings
from connectors.utils import get_connector_conf
import re

_globals_initialized = False
def init_globals():
    global DEBUG, PROXY, API_KEY, TEMPERATURE, TOP_P, TOP_K, MAX_OUTPUT_TOKENS, MODEL
    global _globals_initialized
    if not _globals_initialized:
        DEBUG = False
        PROXY = settings.PROXY
        API_KEY = get_connector_conf('gemini', 'API_KEY')
        MODEL = get_connector_conf('gemini', 'MODEL')
        TEMPERATURE = float(get_connector_conf('gemini', 'TEMPERATURE'))
        TOP_P = float(get_connector_conf('gemini', 'TOP_P'))
        TOP_K = int(get_connector_conf('gemini', 'TOP_K'))
        MAX_OUTPUT_TOKENS = int(get_connector_conf('gemini', 'MAX_OUTPUT_TOKENS'))
        _globals_initialized = True

def get_requirements():
    """
    Return the required modules for the connector.
    """
    init_globals()
    return ['google-genai']

def get_mitre_techniques_from_query(query):
    init_globals()

    client = genai.Client(api_key=API_KEY)

    prompt = f"""
    List only the MITRE ATT&CK TTP IDs (e.g., T1059, T1021.002) that match this query. No descriptions, no explanation.

    Query:
    {query}
    """

    config = GenerateContentConfig(
        temperature=TEMPERATURE,
        top_p=TOP_P,
        top_k=TOP_K,
        max_output_tokens=MAX_OUTPUT_TOKENS
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=config
    )

    mitre_ttps = re.findall(r'T\d{4}(?:\.\d{3})?', response.text)

    return list(set(mitre_ttps))

def write_query_with_ai(prompt):
    init_globals()

    client = genai.Client(api_key=API_KEY)

    config = GenerateContentConfig(
        temperature=TEMPERATURE,
        top_p=TOP_P,
        top_k=TOP_K,
        max_output_tokens=MAX_OUTPUT_TOKENS
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=config
    )

    return response.text
