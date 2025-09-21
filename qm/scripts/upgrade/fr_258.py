"""
FR #258 - Add OpenAI connector
This script adds creates the openai connector and its parameters in DB.

To run:
$ source /data/venv/bin/activate
(venv) $ cd /data/deephunter/
(venv) $ python manage.py runscript upgrade.fr_258
"""

from connectors.models import Connector, ConnectorConf

def run():
    connector, created = Connector.objects.get_or_create(name='openai', defaults={
        'description': """ChatGPT is a generative artificial intelligence chatbot developed by OpenAI and released in 2022. It currently uses GPT-5, a generative pre-trained transformer (GPT), to generate text, speech, and images in response to user prompts.
        
This plugin integrates OpenAI's ChatGPT to suggest MITRE techniques based on a given query.""",
        'enabled': False,
        'domain': 'ai',
    })
    if created:
        print("Created 'OpenAI' connector")
    else:
        print("'OpenAI' connector already exists")

    connectorconf_to_add = [
        {
            'key': 'API_KEY',
            'value': '****************',
            'description': 'Get an API key: https://platform.openai.com/account/api-keys',
            'fieldtype': 'password',
        },
        {
            'key': 'MODEL',
            'value': 'gpt-5',
            'description': """"gpt-5 by default.""",
            'fieldtype': 'char',
        }
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