#!/bin/bash
# DeepHunter installer script
# Version 2.4
# This script will install DeepHunter v2.4 on a Ubuntu Server, with MariaDB as database, and Apache as web server with WSGI and a self-signed certificate.
set -euo pipefail

### Modify these variables as needed
#
export APP_PATH="/data/deephunter"
export VENV_PATH="/data/venv"
export TEMP_FOLDER="/data/tmp"

### Don't modify anything below this line unless you know what you're doing
#

############ 
# Prompt for passwords
#
read -s -p "Enter MySQL 'root' password: " MYSQL_ROOT_PWD
echo
read -s -p "Enter MySQL 'deephunter' password: " MYSQL_DEEPHUNTER_PWD
echo
read -s -p "Enter Django 'admin' password: " DJANGO_SUPERUSER_PWD
echo

############ 
# Remove any existing installation
# Create application directory
#
echo "CREATING DIRECTORIES ...................................................... "
rm -fR $APP_PATH
rm -fR $VENV_PATH
rm -fR $TEMP_FOLDER
sudo mkdir -p $(dirname $APP_PATH)
sudo chown -R $(id -nu):$(id -ng) $(dirname $APP_PATH)
chmod -R 755 $(dirname $APP_PATH)
mkdir -p $APP_PATH
sudo mkdir -p $(dirname $VENV_PATH)
sudo chown -R $(id -nu):$(id -ng) $(dirname $VENV_PATH)
chmod -R 755 $(dirname $VENV_PATH)

############ 
# Update and install dependencies
#
echo "INSTALLING REQUIRED PACKAGES ...................................................... "
sudo apt update
sudo apt install -y git wget gnupg dos2unix \
    python3-venv python3-wheel python3-dev \
    build-essential pkg-config \
    mariadb-server libmariadb-dev \
    apache2 apache2-utils libapache2-mod-wsgi-py3 \
    redis

############ 
# Secure MySQL installation non-interactively
#
echo "MYSQL SECURE INSTALL ...................................................... "
sudo mysql <<-EOSQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PWD}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
EOSQL

############ 
# Create the DeepHunter database and user
#
echo "CREATE DATABASE ...................................................... "
mysql -u root -p"$MYSQL_ROOT_PWD" <<-EOSQL
CREATE DATABASE deephunter;
CREATE USER 'deephunter'@'localhost' IDENTIFIED BY '${MYSQL_DEEPHUNTER_PWD}';
GRANT ALL PRIVILEGES ON deephunter.* TO 'deephunter'@'localhost';
FLUSH PRIVILEGES;
EOSQL

############ 
# Download DeepHunter v2.4
#
echo "DOWNLOAD DEEPHUNTER ...................................................... "
cd /tmp/
wget https://github.com/sebastiendamaye/deephunter/archive/refs/tags/v2.4.tar.gz
tar xzf v2.4.tar.gz -C "$APP_PATH" --strip-components=1

############ 
# Build the virtual environment
#
echo "CREATING VIRTUAL ENVIRONMENT ...................................................... "
python3 -m venv $VENV_PATH

############ 
# Install Python dependencies
#
echo "INSTALLING PYTHON DEPENDENCIES ...................................................... "
source $VENV_PATH/bin/activate
cd $APP_PATH
pip install -r requirements.txt
deactivate
chmod -R 755 $VENV_PATH

############# 
# Make settings adjustments
#
echo "PREPARING SETTINGS FILE ...................................................... "
cd $APP_PATH/deephunter/
cp settings.example.py settings.py

# SECRET_KEY
source $VENV_PATH/bin/activate
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
deactivate
# Escape problematic characters for sed
ESCAPED_SECRET_KEY=$(printf '%s\n' "$SECRET_KEY" | sed 's/[&/\]/\\&/g')
# Replace in settings.py
sed -i "s|^SECRET_KEY = '.*'|SECRET_KEY = '${ESCAPED_SECRET_KEY}'|" settings.py

# DEBUG - set to True for installation and testing, set to False for production
sed -i "s|^DEBUG = .*|DEBUG = True|" settings.py

# PATHS
sed -i "s|^TEMP_FOLDER = .*|TEMP_FOLDER = \"${TEMP_FOLDER}\"|" settings.py
sed -i "s|^VENV_PATH = .*|VENV_PATH = \"${VENV_PATH}\"|" settings.py

# ALLOWED_HOSTS - set to server's IP address
IP_ADDRESS=$(ip route get 1.1.1.1 2>/dev/null | sed -n 's/.*src \([0-9.]*\).*/\1/p')
sed -i "s|^ALLOWED_HOSTS = .*|ALLOWED_HOSTS = ['${IP_ADDRESS}']|" settings.py

# AUTH_PROVIDER - set to local (empty string)
sed -i "s|^AUTH_PROVIDER = .*|AUTH_PROVIDER = ''|" settings.py

# User group
sed -i "s|^USER_GROUP = .*|USER_GROUP = \"$(id -nu):$(id -ng)\"|" settings.py

# MySQL password
sed -i "s|'PASSWORD': '.*'|'PASSWORD': '$MYSQL_DEEPHUNTER_PWD'|" settings.py

# Set proxy to empty
sed -i "s|'http://proxy:port'|''|g" settings.py

# Fix line endings
dos2unix settings.py


#############
# Create initial database and load initial data
#

echo "CREATE INITIAL DATABASE ...................................................... "
# First temporarily disable signals.
sed -i 's/import qm.signals/pass #import qm.signals/' $APP_PATH/qm/apps.py

# create the initial database schema:
source $VENV_PATH/bin/activate
cd $APP_PATH
./manage.py makemigrations qm
./manage.py makemigrations extensions
./manage.py makemigrations reports
./manage.py makemigrations connectors
./manage.py makemigrations repos
./manage.py makemigrations notifications
./manage.py makemigrations dashboard
./manage.py makemigrations config
./manage.py makemigrations
./manage.py migrate

#############
# Create Django super user (prerequisite before loading initial data to get at least 1 user to link to)
#
echo "CREATING DJANGO ADMIN USER ...................................................... "
DJANGO_SUPERUSER_USERNAME=admin \
DJANGO_SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PWD} \
DJANGO_SUPERUSER_EMAIL=admin@localhost \
python manage.py createsuperuser --no-input

echo "LOAD INITIAL DATA ...................................................... "
# load initial data from fixtures
./manage.py loaddata install/fixtures/qm_country.json
./manage.py loaddata install/fixtures/qm_threatactor.json
./manage.py loaddata install/fixtures/qm_threatname.json
./manage.py loaddata install/fixtures/qm_vulnerability.json
./manage.py loaddata install/fixtures/qm_mitretactic.json
./manage.py loaddata install/fixtures/qm_mitretechnique.json
./manage.py loaddata install/fixtures/qm_tag.json
./manage.py loaddata install/fixtures/qm_category.json
./manage.py loaddata install/fixtures/qm_targetos.json
./manage.py loaddata install/fixtures/qm_savedsearch.json
./manage.py loaddata install/fixtures/config.json

# connector fixture has been updated (bug fix)
sed -i 's|"visible_in_analytics": true|"domain": "analytics"|' install/fixtures/connectors.json
sed -i 's|"visible_in_analytics": false|"domain": ""|' install/fixtures/connectors.json
./manage.py loaddata install/fixtures/connectors.json

./manage.py loaddata install/fixtures/qm_analytic.json

deactivate

# Restore signals:
sed -i 's/pass #import qm.signals/import qm.signals/' $APP_PATH/qm/apps.py

echo "FIX PERMISSIONS ...................................................... "
# Fix permissions
chmod -R 755 $APP_PATH
touch $APP_PATH/static/mitre.json
chmod 666 $APP_PATH/static/mitre.json

#############
# Configure Apache
#
echo "CONFIGURING APACHE2 ...................................................... "
sudo a2enmod headers

# Create a self-signed certificate
cd $APP_PATH/install/scripts/
chmod +x ./generate_deephunter_self_cert.sh
./generate_deephunter_self_cert.sh deephunter.localtest.me
sudo a2enmod ssl

# improve your encryption by creating a strong DH Group, and enable Perfect Forward Secrecy:
sudo cp $APP_PATH/install/etc/apache2/conf-available/ssl-params.conf /etc/apache2/conf-available/
sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
sudo a2enconf ssl-params

# Enable site in HTTPS
sed -i "s|/data/deephunter|${APP_PATH}|" $APP_PATH/install/etc/apache2/sites-available/deephunter-ssl.conf
sudo cp $APP_PATH/install/etc/apache2/sites-available/deephunter-ssl.conf /etc/apache2/sites-available/
sudo a2ensite deephunter-ssl


#############
# Install celery
#
echo "CONFIGURING CELERY ...................................................... "

sed -i "s|/data/venv|${VENV_PATH}|" $APP_PATH/install/etc/default/celery
sudo cp $APP_PATH/install/etc/default/celery /etc/default/celery

# On Ubuntu Server, it seems that the /var/run/ directory is purged at each reboot.
# To make sure the celery subdirectory is recreated at each boot, you can create the following file
echo 'd /var/run/celery 0755 celery celery' | sudo tee /etc/tmpfiles.d/celery.conf > /dev/null

# create the celery user and group.
sudo groupadd celery
sudo useradd -g celery celery

# Create the directories and fix permissions:
sudo mkdir /var/run/celery/
sudo chown celery:celery /var/run/celery/
sudo mkdir /var/log/celery/
sudo chown celery:celery /var/log/celery/


# To start the Celery service automatically, you may want to create a file in /etc/systemd/system/celery.service as follows:
sudo cp $APP_PATH/install/etc/systemd/system/celery.service /etc/systemd/system/celery.service

# Reload services and enable them:
sudo systemctl daemon-reload
sudo systemctl enable celery.service
sudo systemctl start celery.service

# Restart services to apply all changes
echo "RESTARTING SERVICES ...................................................... "
sudo systemctl restart apache2
sudo systemctl restart redis

echo
echo "INSTALLATION COMPLETE ...................................................... "
echo
echo "You can now access DeepHunter at https://${IP_ADDRESS}/"
echo "Login with username 'admin' and the password you provided during installation."
echo
echo "Go to Admin > Settings > Connectors and update the settings as needed."
echo
echo "Post-installation recommendations:
echo "- Change the admin password if local admin is required."
echo "- Set DEBUG to False in $APP_PATH/deephunter/settings.py"
echo
