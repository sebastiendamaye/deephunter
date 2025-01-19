#!/bin/bash

# Prompt for MySQL root password and deephunter user password
read -s -p "Enter MySQL root password: " MYSQL_ROOT_PASSWORD
echo
read -s -p "Enter password for deephunter user: " DEEPHUNTER_PASSWORD
echo

echo "Starting installation of DeepHunter..."

# Function to check the status of the last command and exit if failed
check_status() {
  if [ $? -ne 0 ]; then
    echo "Error: $1 failed. Exiting."
    exit 1
  fi
}

# Update and install necessary packages
sudo apt update
check_status "apt update"

sudo apt install -y python3-venv python3-wheel python3-dev default-libmysqlclient-dev
check_status "installing Python packages"

sudo apt install -y build-essential pkg-config
check_status "installing build-essential and pkg-config"

sudo apt install -y mariadb-server libmariadb-dev
check_status "installing MariaDB"

sudo apt install -y git apache2 apache2-utils libapache2-mod-wsgi-py3
check_status "installing Apache and mod-wsgi"

sudo apt install -y redis
check_status "installing Redis"

# Create /data directory and set permissions
sudo mkdir -p /data
sudo chmod -R 755 /data
check_status "creating /data directory"

# Create and activate Python virtual environment
python3 -m venv /data/venv
check_status "creating Python virtual environment"

source /data/venv/bin/activate
check_status "activating Python virtual environment"

# Install Python dependencies
pip install -r /data/deephunter/requirements.txt
check_status "installing Python dependencies"

# Install and configure MariaDB
sudo mysql_secure_installation
check_status "securing MariaDB installation"

sudo mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "create database deephunter;"
check_status "creating deephunter database"

sudo mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "create user 'deephunter'@'localhost' identified by '$DEEPHUNTER_PASSWORD';"
check_status "creating deephunter user"

sudo mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "grant all privileges on deephunter.* to 'deephunter'@'localhost';"
check_status "granting privileges to deephunter user"

# Download DeepHunter
cd /data
sudo git clone https://github.com/sebastiendamaye/deephunter.git
check_status "cloning DeepHunter repository"

# Initialize the database
source /data/venv/bin/activate
/data/venv/bin/python /data/deephunter/manage.py makemigrations
check_status "making migrations"

/data/venv/bin/python /data/deephunter/manage.py migrate
check_status "migrating database"

# Configure and restart Apache2 with SSL and mod-wsgi
sudo a2enmod ssl
check_status "enabling SSL module"

sudo a2enmod headers
check_status "enabling headers module"

sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
check_status "creating dhparam.pem"

sudo a2enconf ssl-params
check_status "enabling SSL parameters configuration"

sudo a2ensite deephunter-ssl
check_status "enabling deephunter-ssl site"

sudo systemctl restart apache2
check_status "restarting Apache2"

# Setup Celery
sudo groupadd celery
check_status "creating celery group"

sudo useradd -g celery celery
check_status "creating celery user"

# Fix permissions
sudo chmod -R 755 /data
sudo chmod 666 /data/deephunter/campaigns.log
sudo chmod 666 /data/deephunter/static/mitre.json
check_status "fixing permissions"

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
check_status "creating Celery service file"

# Reload services and enable Celery service
sudo systemctl daemon-reload
sudo systemctl enable celery.service
sudo systemctl start celery.service
check_status "starting Celery service"

# Install initial data
source /data/venv/bin/activate
/data/venv/bin/python /data/deephunter/manage.py loaddata fixtures/authgroup.json
check_status "loading authgroup.json"
/data/venv/bin/python /data/deephunter/manage.py loaddata fixtures/mitretactic.json
check_status "loading mitretactic.json"
/data/venv/bin/python /data/deephunter/manage.py loaddata fixtures/mitretechnique.json
check_status "loading mitretechnique.json"
/data/venv/bin/python /data/deephunter/manage.py loaddata fixtures/tag.json
check_status "loading tag.json"
/data/venv/bin/python /data/deephunter/manage.py loaddata fixtures/targetos.json
check_status "loading targetos.json"
/data/venv/bin/python /data/deephunter/manage.py loaddata fixtures/query.json
check_status "loading query.json"

echo "DeepHunter installation completed."
