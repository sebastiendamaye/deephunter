Develop your own
################

Description
***********
You may want to develop your own tools, it's easy to do. All you need to do is add a HTML template for the frontend, and add a function to the `views.py` file.

File structure
**************
Tools are called `extensions` in DeepHunter, and should be located in the `extensions` folder, which has the following structure:

.. code-block:: sh

	./extensions/
	├── __init__.py
	├── admin.py
	├── apps.py
	├── models.py
	├── templates
	│   ├── loldriverhashchecker.html
	│   ├── vthashchecker.html
	│   └── whois.html
	├── tests.py
	├── urls.py
	└── views.py

All you need to do is add a template in the `templates` folder, and add your function to the `views.py` file.
