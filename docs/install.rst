Installation
############

Compatibility
*************
DeepHunter has been designed to run on a Linux environment. Ubuntu Server or Debian are the recommended OS to install DeepHunter.

Build the python virtual environment
************************************

It is highly recommended that you install DeepHunter in a Python virtual environment. There are several tools to do that (Conda, Poetry, etc). We'll use ``venv``.

We'll assume that you have created a ``/data`` directory and you have write access to it.

.. code-block:: sh
      
   $ sudo apt install python3-venv python3-wheel python3-dev default-libmysqlclient-dev
   $ sudo apt install build-essential pkg-config
   $ cd /data
   $ chmod -R 755 /data/
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

Install the python dependencies
*******************************

Enter the virtual environment and install dependencies from the ``requirements.txt`` file:

.. code-block:: sh
	
	$ source /data/venv/bin/activate
	(venv) $ cd deephunter/
	(venv) $ pip install -r requirements.txt

Download DeepHunter
*******************
To download DeepHunter, use the following git command:

.. code-block:: sh

	$ cd /data/
	$ git clone https://github.com/sebastiendamaye/deephunter.git

Initialization
**************
Make sure you configure all necessary `settings <settings.html>`_ for your environment.

Once done, initialize the database:

.. code-block:: sh

	$ source /data/venv/bin/activate
	(venv) $ ./manage makemigrations
	(venv) $ ./manage migrate

Try to run ``./manage.py runserver`` on default port 8000 and confirm that there is no error

Apache2 mod-wsgi
****************
There are several ways of `running Django applications in production <https://docs.djangoproject.com/en/5.1/howto/deployment/>``. We'll user ``Apache2`` and ``mod-wsgi`` here.

.. code-block:: sh

	$ sudo apt install apache2 apache2-utils libapache2-mod-wsgi-py3

Enable SSL:

.. code-block:: sh

	$ sudo a2enmod ssl

Enable mod headers

.. code-block:: sh

	$ sudo a2enmod headers

Below line is mandatory because ``dhparam.pem`` is required in ``ssl-params.conf``. Improve your encryption by creating a strong DH Group, and enable Perfect Forward Secrecy.

.. code-block:: sh

	$ sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
	$ sudo a2enconf ssl-params
	$ sudo a2ensite deephunter-ssl

Restart apache2:

.. code-block:: sh

	$ sudo systemctl restart apache2

Crontab (standard user)
***********************

You can use the crontab in ``qm/scripts/crontab``.

.. code-block:: sh

	# m h  dom mon dow   command
	0  4 * * *      /data/deephunter/qm/scripts/run_campaign.sh
	30 5 * * *      /data/deephunter/qm/scripts/optimize_db.sh
	0  6 * * *      /data/deephunter/qm/scripts/backup.sh

For details about the scripts, see the `scripts page <scripts.html>`_.

Encrypted backups
*****************
To backup your database, it is recommended to use ``django-dbbackup`` and run the job via crontab.

.. code-block:: sh

	(venv) $ pip install django-dbbackup
	(venv) $ pip install python-gnupg>=0.5.0

Generate a PGP key and set ``DBBACKUP_GPG_RECIPIENT`` to recipient in ``settings.py``.

Import PGP keys, both public and private.

Below is the command to make an encrypted backup:

.. code-block:: sh

	(venv) $ ./manage.py dbbackup --encrypt

To restore from an encrypted backup, run the following command:

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

Fix permissions:

.. code-block:: sh

	$ chmod -R 755 /data
	$ chmod 666 /data/deephunter/campaigns.log 
	$ chmod 666 /data/deephunter/static/mitre.json 

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

Install initial data
********************
DeepHunter is shipped with some data (fixtures). To install them, run the following commands:

.. code-block:: sh

	$ source /data/venv/bin/activate
	(venv) $ ./manage.py loaddata fixtures/authgroup.json
	(venv) $ ./manage.py loaddata fixtures/mitretactic.json
	(venv) $ ./manage.py loaddata fixtures/mitretechnique.json
	(venv) $ ./manage.py loaddata fixtures/tag.json
	(venv) $ ./manage.py loaddata fixtures/targetos.json
	(venv) $ ./manage.py loaddata fixtures/query.json

Notice that you will need to populate some tables yourself (threat actors, threat names, vulnerabilities, etc.) depending on the future queries you will create in DeepHunter. Creating new queries in DeepHunter is explained `here <admin.html#create-modify-threat-hunting-analytics>`_.

Upgrading DeepHunter
********************
When an update is available, you can upgrade DeepHunter as follows:

.. code-block:: sh

	$ cd /data
	$ ./deephunter/qm/scripts/upgrade.sh
