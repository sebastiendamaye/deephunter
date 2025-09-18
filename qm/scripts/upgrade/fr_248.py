"""
FR #248 - Use AI to automatically populate MITRE coverage for newly created analytics based on query and/or references
This script adds creates the gemini connector and its parameters in DB.

To run:
$ source /data/venv/bin/activate
(venv) $ cd /data/deephunter/
(venv) $ python manage.py runscript upgrade.fr_248
"""

from connectors.models import Connector, ConnectorConf

def run():
    connector, created = Connector.objects.get_or_create(name='gemini', defaults={
        'description': """google-genai (https://github.com/googleapis/python-genai) is an initial Python client library for interacting with Google’s Generative AI APIs.

Google Gen AI Python SDK provides an interface for developers to integrate Google’s generative models into their Python applications. It supports the Gemini Developer API and Vertex AI APIs.""",
        'enabled': False,
        'domain': 'ai',
    })
    if created:
        print("Created 'Gemini' connector")
    else:
        print("'Gemini' connector already exists")

    connectorconf_to_add = [
        {
            'key': 'API_KEY',
            'value': '****************',
            'description': 'Get an API key: https://aistudio.google.com/app/apikey',
        },
        {
            'key': 'MODEL',
            'value': 'gemini-1.5-flash',
            'description': """"gemini-1.5-flash" (~128K tokens, good for basic tasks) or "gemini-2.5-flash" (1M+ tokens, Higher quality, better reasoning)""",
        },
        {
            'key': 'TEMPERATURE',
            'value': '0.0',
            'description': """Controls randomness / creativity of the model.
0.0 = deterministic → same input always gives same output.
Higher values (e.g. 0.7) allow more variety or creative phrasing.
Best for: consistent, factual, extractive outputs.""",
        },
        {
            'key': 'TOP_P',
            'value': '1.0',
            'description': """Also known as nucleus sampling.
The model picks from the smallest set of words whose total probability adds up to top_p.
1.0 means use the entire probability distribution (no filtering).
Lower values (e.g. 0.8) force more focused outputs but can reduce variety.""",
        },
        {
            'key': 'TOP_K',
            'value': '0',
            'description': """Limits the model to selecting from the top K most likely next tokens.
0 means no limit — let top_p fully control the sampling.
If set to e.g. top_k=40, the model only chooses from the top 40 likely options.
Best left at 0 when using top_p=1.0.""",
        },
        {
            'key': 'MAX_OUTPUT_TOKENS',
            'value': '128',
            'description': """Caps the length of the model's response (number of tokens).
128 tokens ≈ ~90–100 words (depending on the language and structure).
Set higher if you expect longer responses.""",
        },
    ]

    for conf in connectorconf_to_add:
        connector_conf, created = ConnectorConf.objects.get_or_create(
            connector=connector,
            key=conf['key'],
            defaults={
                'value': conf['value'],
                'description': conf['description'],
            }
        )
        if created:
            print(f"Added connector key: {conf['key']} ({conf['value']})")
        else:
            print(f"Connector key already exists: {conf['key']}")