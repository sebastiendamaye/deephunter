Gemini
######

Description
***********
Gemini is a generative artificial intelligence chatbot developed by Google AI. Based on the large language model of the same name, it was launched in February 2024.

This connector is used to automatically populate MITRE coverage for analytics based on the query field.

Settings
********

API_KEY
=======

- **Type**: string
- **Description**: Get an API key: https://aistudio.google.com/app/apikey.
- **Example**: 

.. code-block:: python

	API_KEY = 'bffgwLSmWs9cmnkhqsGei'

MODEL
=====

- **Type**: string
- **Description**: gemini-1.5-flash" (~128K tokens, good for basic tasks) or "gemini-2.5-flash" (1M+ tokens, Higher quality, better reasoning).
- **Example**: 

.. code-block:: python

	MODEL = 'gemini-1.5-flash'

TEMPERATURE
===========

- **Type**: float
- **Description**: Controls randomness / creativity of the model. 0.0 = deterministic → same input always gives same output. Higher values (e.g. 0.7) allow more variety or creative phrasing. Best for: consistent, factual, extractive outputs.
- **Example**: 

.. code-block:: python

    TEMPERATURE = 0.0

TOP_P
=====

- **Type**: float
- **Description**: Also known as nucleus sampling. The model picks from the smallest set of words whose total probability adds up to top_p. 1.0 means use the entire probability distribution (no filtering). Lower values (e.g. 0.8) force more focused outputs but can reduce variety.
- **Example**: 

.. code-block:: python

	TOP_P = 1.0

TOP_K
=====

- **Type**: integer
- **Description**: Limits the model to selecting from the top K most likely next tokens. 0 means no limit — let top_p fully control the sampling. If set to e.g. top_k=40, the model only chooses from the top 40 likely options. Best left at 0 when using top_p=1.0.
- **Example**: 

.. code-block:: python

    TOP_K = 0

MAX_OUTPUT_TOKENS
=================

- **Type**: integer
- **Description**: Caps the length of the model's response (number of tokens). 128 tokens ≈ ~90–100 words (depending on the language and structure). Set higher if you expect longer responses.
- **Example**: 

.. code-block:: python

    MAX_OUTPUT_TOKENS = 128
