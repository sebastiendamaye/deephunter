#!/bin/bash

# Prompt for MySQL root password and deephunter user password
read -s -p "Enter MySQL root password: " MYSQL_ROOT_PASSWORD
echo
read -s -p "Enter password for deephunter user: " DEEPHUNTER_PASSWORD
echo

echo "Starting installation of DeepHunter..."

# Update and install necessary packages
sudo apt update
sudo apt install -y python3-venv python3-wheel python3-dev default-libmysqlclient-dev
sudo apt install -y build-essential pkg-config
sudo apt install -y mariadb-server libmariadb-dev
sudo apt install -y git apache2 apache2-utils libapache2-mod-wsgi-py3
sudo apt install -y redis

# Create /data directory and set permissions
sudo mkdir -p /data
sudo chmod -R 755 /data

# Create and activate Python virtual environment
python3 -m venv /data/venv
source /data/venv/bin/activate

# Install Python dependencies
pip install -r /data/deephunter/requirements.txt

# Install and configure MariaDB
sudo mysql_secure_installation
sudo mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "create database deephunter;"
sudo mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "create user 'deephunter'@'localhost' identified by '$DEEPHUNTER_PASSWORD';"
sudo mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "grant all privileges on deephunter.* to 'deephunter'@'localhost';"

# Download DeepHunter
cd /data
sudo git clone https://github.com/sebastiendamaye/deephunter.git

# Initialize the database
source /data/venv/bin/activate
/data/venv/bin/python /data/deephunter/manage.py makemigrations
/data/venv/bin/python /data/deephunter/manage.py migrate

# Configure and restart Apache2 with SSL and mod-wsgi
sudo a2enmod ssl
sudo a2enmod headers
sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
sudo a2enconf ssl-params
sudo a2ensite deephunter-ssl
sudo systemctl restart apache2

# Setup Celery
sudo groupadd celery
sudo useradd -g celery celery

# Fix permissions
sudo chmod -R 755 /data
sudo chmod 666 /data/deephunter/campaigns.log
sudo chmod 666 /data/deephunter/static/mitre.json

# Create Celery service file
cat <<EOT | sudo tee /etc/systemd/system/celery.service
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=celery
Group=celery
EnvironmentFile=/etc/default/celery
WorkingDirectory=/data/deephunter
ExecStart=/bin/sh -c '\${CELERY_BIN} -A \$CELERY_APP multi start \$CELERYD_NODES \
  --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} \
  --loglevel="\${CELERYD_LOG_LEVEL}" \$CELERYD_OPTS'
ExecStop=/bin/sh -c '\${CELERY_BIN} multi stopwait \$CELERYD_NODES \
  --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} \
  --loglevel="\${CELERYD_LOG_LEVEL}"'
ExecReload=/bin/sh -c '\${CELERY_BIN} -A \$CELERY_APP multi restart \$CELERYD_NODES \
  --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} \
  --loglevel="\${CELERYD_LOG_LEVEL}" \$CELERYD_OPTS'
Restart=always

[Install]
WantedBy=multi-user.target
EOT

# Reload services and enable Celery service
sudo systemctl daemon-reload
sudo systemctl enable celery.service
sudo systemctl start celery.service

# Install initial data
source /data/venv/bin/activate
/data/venv/bin/python /data/deephunter/manage.py loaddata fixtures/authgroup.json
/data/venv/bin/python /data/deephunter/manage.py loaddata fixtures/mitretactic.json
/data/venv/bin/python /data/deephunter/manage.py loaddata fixtures/mitretechnique.json
/data/venv/bin/python /data/deephunter/manage.py loaddata fixtures/tag.json
/data/venv/bin/python /data/deephunter/manage.py loaddata fixtures/targetos.json
/data/venv/bin/python /data/deephunter/manage.py loaddata fixtures/query.json

echo "DeepHunter installation completed."
