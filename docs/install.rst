Installation
############

Compatibility
*************
DeepHunter has been designed to run on a Linux environment. Ubuntu Server or Debian are the recommended OS to install DeepHunter.

Build the python virtual environment
************************************

It is highly recommended that you install DeepHunter in a Python virtual environment. There are several tools to do that (Conda, Poetry, etc). We'll use ``venv``.

We'll install DeepHunter in ``/data/deephunter/`` and the Python virtual environment in ``/data/venv/``. Adapt the procedure if you choose different folders.

.. code-block:: sh
      
   $ sudo apt install python3-venv python3-wheel python3-dev default-libmysqlclient-dev
   $ sudo apt install build-essential pkg-config
   $ sudo mkdir /data
   $ sudo chown -R $(id -nu):$(id -ng) /data
   $ chmod -R 755 /data/
   $ cd /data
   $ python3 -m venv venv

Install the database
********************

.. code-block:: sh

	$ sudo apt install mariadb-server libmariadb-dev
	$ sudo mysql_secure_installation
	$ mysql -u root -p
	mysql> create database deephunter;
	mysql> create user deephunter@localhost identified by 'Awes0meP4ssW0rd';
	mysql> grant all privileges on deephunter.* to deephunter@localhost;
	mysql> \q

Download DeepHunter
*******************

To download DeepHunter, use the following git command:

.. code-block:: sh

	$ sudo apt install git
	$ cd /data/
	$ git clone https://github.com/sebastiendamaye/deephunter.git

While cloning the repo as explained above will give you access to the latest features, you may prefer to install the `latest stable release <https://github.com/sebastiendamaye/deephunter/releases/latest>`_.

Install the python dependencies
*******************************

Enter the virtual environment and install dependencies from the ``requirements.txt`` file:

.. code-block:: sh
	
	$ source /data/venv/bin/activate
	$ cd /data/deephunter/
	(venv) $ pip install -r requirements.txt

NOTE: To manage the session timeout, DeepHunter relies on the `django-auto-logout <https://pypi.org/project/django-auto-logout/>`_ package, that is not `CSP <https://content-security-policy.com/>`_ compliant. If you care about CSP compliance, use the following patch (notice that you will need to patch the file each time the package will be updated). Also make sure you use the same ID in your `/etc/apache2/conf-available/security.conf` file.

.. code-block:: sh
        
        $ VENV_PATH="/data/venv"
        $ LIB_PATH=$(find $VENV_PATH -type d -name django_auto_logout 2>/dev/null)
        $ sed -i "s/<script>/<script nonce=\"kj5fcv07a2\">/" $LIB_PATH/context_processors.py

Initialization
**************

Rename ``settings.example.py`` to ``settings.py``:

.. code-block:: sh
	
	$ cd /data/deephunter/deephunter/
	$ mv settings.example.py settings.py

Now edit ``settings.py`` and make sure you configure all necessary `settings <settings.html>`_ for your environment.

Once done, initialize the database:

.. code-block:: sh

	$ source /data/venv/bin/activate
	(venv) $ ./manage.py makemigrations
        (venv) $ ./manage.py makemigrations qm
	(venv) $ ./manage.py migrate

Try to run ``./manage.py runserver`` on default port 8000 and confirm that there is no error

Apache2 mod-wsgi
****************

There are several ways of `running Django applications in production <https://docs.djangoproject.com/en/5.1/howto/deployment/>`_. We'll use ``Apache2`` and ``mod-wsgi`` here.

Note: you'll find some configuration file examples in the ``install`` directory. Make sure you have all these files before running the below commands. You may need to customize them to fit with your environment.

Install Apache2 and necessary modules
=====================================

Let's start by install Apache2 server and some necessary modules.

.. code-block:: sh

	$ sudo apt install apache2 apache2-utils libapache2-mod-wsgi-py3

Enable mod headers

.. code-block:: sh

	$ sudo a2enmod headers

Certificate
===========

You first need to generate a certificate for Apache2.

For a development environment or for testing purposes, you may use a self-signed certificate. You can use the script ``/data/deephunter/install/scripts/generate_deephunter_self_cert.sh`` to generate a self-signed SSL certificate (``deephunter.cer``) and a private key (``deephunter.key``) for the ``deephunter-ssl.conf`` configuration file.

Make the script executable and run it with the domain as a parameter (``deephunter.localtest.me`` used below as example):

.. code-block:: sh
	
	$ cd /data/deephunter/install/scripts/
	$ chmod +x ./generate_deephunter_self_cert.sh
	$ ./generate_deephunter_self_cert.sh deephunter.localtest.me

This will generate the SSL certificate and key files for the specified domain.

Note: ``localtest.me`` is a public domain that resolves to ``127.0.0.1`` (IPv4) and ``::1`` (IPv6).

SSL and enforcement
===================

Now, we'll make sure DeepHunter is served on port 443 via HTTPS.

.. code-block:: sh

	$ sudo a2enmod ssl

**Optional**: In a production environment, improve your encryption by creating a strong DH Group, and enable Perfect Forward Secrecy:

.. code-block:: sh
	
	$ sudo cp /data/deephunter/install/etc/apache2/conf-available/ssl-params.conf /etc/apache2/conf-available/
	$ sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
	$ sudo a2enconf ssl-params

Enable HTTPS
============

Now, run the following commands to enable DeepHunter in HTTPS:

.. code-block:: sh

	$ sudo cp /data/deephunter/install/etc/apache2/sites-available/deephunter-ssl.conf /etc/apache2/sites-available/
	$ sudo nano -c /etc/apache2/sites-enabled/deephunter-ssl.conf
	$ sudo a2ensite deephunter-ssl

Restart Apache2
===============

Now, restart Apache2:

.. code-block:: sh

	$ sudo systemctl restart apache2

Crontab (standard user)
***********************

You can use the crontab in ``install/scripts/crontab``.

.. code-block:: sh
	
	# m h  dom mon dow   command
	1  0 * * *      /data/deephunter/qm/scripts/orchestrator.sh
	0  2 * * *      /data/deephunter/qm/scripts/optimize_db.sh
	0  4 * * *      /data/deephunter/qm/scripts/backup.sh

For details about the scripts, see the `scripts page <scripts.html>`_.

Encrypted backups
*****************

Install django-dbbackup
=======================

To backup your database, it is recommended to use ``django-dbbackup`` and run the job via crontab. It is also recommended to encrypt database backups (encryption works with PGP/GPG).

.. code-block:: sh

	(venv) $ pip install python-gnupg>=0.5.0
	(venv) $ pip install django-dbbackup

Generate PGP keys
=================

Generating a PGP key on Linux is a straightforward process. Here's a step-by-step guide to help you get started:

- First, make sure you have GnuPG installed. On Debian-based OS (e.g., Ubuntu), you can run the below command:

.. code-block:: sh
	
	sudo apt-get install gnupg

- Generate a new PGP key:

.. code-block:: sh

	gpg --full-generate-key

- You'll be prompted to choose the type of key you want. The default option (RSA) is usually fine. Then, you'll need to specify the key size (2048 bits should be sufficient for most use cases, balancing security and performance) and the key's expiration date.

- Enter the details: You'll be asked to enter your name, email address, and an optional comment. This information will be associated with your key.

- Set a Passphrase: Choose a strong passphrase to protect your private key.

- Key Generation: GnuPG will generate your key pair. This might take a few moments.

- Verify Your Key: You can list your keys to verify that the new key has been created:

.. code-block:: sh

	gpg --list-keys

Configure dbbackup
==================

Make sure you set `DBBACKUP_GPG_RECIPIENT <settings.html#dbbackup>`_ to the correct recipient (email address) in ``settings.py``.

Backup and restore commands
===========================
- Make sure both your private and public keys are listed by running the below command:

.. code-block:: sh
	
	gpg --list-keys

To make an encrypted backup, run the below command:

.. code-block:: sh

	(venv) $ ./manage.py dbbackup --encrypt

To restore the database from an encrypted backup, run the following command:

.. code-block:: sh

	(venv) $ ./manage.py dbrestore --decrypt -i /data/backups/DB-2025-01-01-070002.dump.gpg
	Input Passphrase: ***********
	Are you sure you want to continue? [Y/n] Y

Async tasks: Celery / Redis (message broker)
********************************************
DeepHnter has a special feature to run commands in the background (i.e., regeneration of statistics). This relies on Celery and Redis. To install these services, run the following commands:

Install the message broker:

.. code-block:: sh

	$ sudo apt update && sudo apt install redis
	$ source /data/venv/bin/activate
	(venv) $ pip install celery
	(venv) $ pip install redis

Modify ``/etc/default/celery`` to fit with your environment. An example is given below.

.. code-block:: sh

	CELERYD_NODES="w1"
	CELERY_BIN="/data/venv/bin/celery"
	CELERY_APP="deephunter"
	CELERYD_MULTI="multi"
	CELERYD_OPTS="--time-limit=3600 --concurrency=3"
	CELERYD_PID_FILE="/var/run/celery/%n.pid"
	CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
	CELERYD_LOG_LEVEL="INFO"
	CELERYD_USER="celery"
	CELERYD_GROUP="celery"
	CELERY_CREATE_DIRS=1

On Ubuntu Server, it seems that the ``/var/run/`` directory is purged at each reboot. To make sure the ``celery`` subdirectory is recreated at each boot, you can create the following file in ``/etc/tmpfiles.d/celery.conf``:

.. code-block:: sh

	d /var/run/celery 0755 celery celery

Now, create the celery user and group.

.. code-block:: sh

	$ sudo groupadd celery
	$ sudo useradd -g celery celery

Create the directories and fix permissions:

.. code-block:: sh

	$ sudo mkdir /var/run/celery/
	$ sudo chown celery:celery /var/run/celery/
	$ sudo mkdir /var/log/celery/
	$ sudo chown celery:celery /var/log/celery/
	$ chmod -R 755 /data
	$ chmod 666 /data/deephunter/campaigns.log 
	$ chmod 666 /data/deephunter/static/mitre.json 
	$ chmod 666 /data/deephunter/static/tokendate.txt

To start the Celery service automatically, you may want to create a file in ``/etc/systemd/system/celery.service`` as follows:

.. code-block:: sh

	[Unit]
	Description=Celery Service
	After=network.target

	[Service]
	Type=forking
	User=celery
	Group=celery
	EnvironmentFile=/etc/default/celery
	WorkingDirectory=/data/deephunter
	ExecStart=/bin/sh -c '${CELERY_BIN} -A $CELERY_APP multi start $CELERYD_NODES \
		--pidfile=${CELERYD_PID_FILE} --logfile=${CELERYD_LOG_FILE} \
		--loglevel="${CELERYD_LOG_LEVEL}" $CELERYD_OPTS'
	ExecStop=/bin/sh -c '${CELERY_BIN} multi stopwait $CELERYD_NODES \
		--pidfile=${CELERYD_PID_FILE} --logfile=${CELERYD_LOG_FILE} \
		--loglevel="${CELERYD_LOG_LEVEL}"'
	ExecReload=/bin/sh -c '${CELERY_BIN} -A $CELERY_APP multi restart $CELERYD_NODES \
		--pidfile=${CELERYD_PID_FILE} --logfile=${CELERYD_LOG_FILE} \
		--loglevel="${CELERYD_LOG_LEVEL}" $CELERYD_OPTS'
	Restart=always

	[Install]
	WantedBy=multi-user.target

Reload services and enable them:

.. code-block:: sh

	$ sudo systemctl daemon-reload
	$ sudo systemctl enable celery.service
	$ sudo systemctl start celery.service
	$ sudo systemctl status celery.service

Note: If you have difficulties to start the service, check if directory ``/var/log/celery`` is present. If not, create it with ``sudo mkdir /var/log/celery/``

Install initial data
********************
DeepHunter is shipped with some data (fixtures). To install them, use the ``load_initial_data.sh`` script:

.. code-block:: sh

	$ /data/deephunter/install/scripts/load_initial_data.sh

Upgrading DeepHunter
********************
When an update is available, you can upgrade DeepHunter as follows:

.. code-block:: sh

	$ cd /data
	$ ./deephunter/qm/scripts/upgrade.sh
