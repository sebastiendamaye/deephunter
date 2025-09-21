OpenAI
######

Description
***********
ChatGPT is a generative artificial intelligence chatbot developed by OpenAI and released in 2022. It currently uses GPT-5, a generative pre-trained transformer (GPT), to generate text, speech, and images in response to user prompts.

This connector is used to automatically populate MITRE coverage for analytics based on the query field.

Settings
********

API_KEY
=======

- **Type**: string
- **Description**: Get an API key: https://platform.openai.com/account/api-keys.
- **Example**: 

.. code-block:: python

	API_KEY = 'sk-4rAnD0mFAk3APIk3y1234567890abcdefg'

MODEL
=====

- **Type**: string
- **Description**: GPT‑5 (the newest flagship model), GPT‑5‑mini (a smaller/faster version, with less cost/latency), GPT‑5‑nano (even smaller/faster, lower cost).
- **Example**: 

.. code-block:: python

	MODEL = 'gpt-5'
