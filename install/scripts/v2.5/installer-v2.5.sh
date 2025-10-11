#!/bin/bash
# DeepHunter installer script
# Version 2.5
# This script will install DeepHunter v2.5 on a Ubuntu Server, with MariaDB as database, and Apache as web server with WSGI and a self-signed certificate.
set -euo pipefail
trap 'echo "ERROR: Script failed at line $LINENO. Check /tmp/install.log."; exit 1' ERR

### Modify these variables as needed
#
export APP_PATH="/data/deephunter"
export VENV_PATH="/data/venv"
export TEMP_FOLDER="/data/tmp"

### Don't modify anything below this line unless you know what you're doing
#
#
export USER_GROUP="$(id -nu):$(id -ng)"
export SERVER_USER="www-data"
echo ""
echo "   ____                  _   _             _            "
echo "  |  _ \  ___  ___ _ __ | | | |_   _ _ __ | |_ ___ _ __ "
echo "  | | | |/ _ \/ _ \ '_ \| |_| | | | | '_ \| __/ _ \ '__|"
echo "  | |_| |  __/  __/ |_) |  _  | |_| | | | | ||  __/ |   "
echo "  |____/ \___|\___| .__/|_| |_|\__,_|_| |_|\__\___|_|   "
echo "                  |_|                                   "
echo ""
echo "            *** DeepHunter Installer v2.5 ***"
echo ""
echo ""

echo > /tmp/install.log

############ 
# Generate random passwords
#
echo -n -e "[\033[90mINFO\033[0m] GENERATING PASSWORDS ............................ " | tee -a /tmp/install.log
# Generate random passwords (32 characters, alphanumeric only)
MYSQL_ROOT_PWD="$(openssl rand -base64 32 | tr -d '=+/ ' | cut -c1-32)"
MYSQL_DEEPHUNTER_PWD="$(openssl rand -base64 32 | tr -d '=+/ ' | cut -c1-32)"
DJANGO_SUPERUSER_PWD="$(openssl rand -base64 32 | tr -d '=+/ ' | cut -c1-32)"
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

############ 
# Remove any existing installation
# Create application directory
#
echo -n -e "[\033[90mINFO\033[0m] CREATING DIRECTORIES ............................ " | tee -a /tmp/install.log
rm -fR ${APP_PATH}
rm -fR $VENV_PATH
rm -fR $TEMP_FOLDER
sudo mkdir -p $(dirname ${APP_PATH})
sudo chown -R $(id -nu):$(id -ng) $(dirname ${APP_PATH})
chmod -R 755 $(dirname ${APP_PATH})
mkdir -p ${APP_PATH}
sudo mkdir -p $(dirname $VENV_PATH)
sudo chown -R $(id -nu):$(id -ng) $(dirname $VENV_PATH)
chmod -R 755 $(dirname $VENV_PATH)
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

############ 
# Update and install dependencies
#
echo -n -e "[\033[90mINFO\033[0m] INSTALLING REQUIRED PACKAGES .................... " | tee -a /tmp/install.log
sudo apt-get update >> /tmp/install.log 2>&1
sudo apt-get install -y git wget gnupg dos2unix \
    python3-venv python3-wheel python3-dev \
    build-essential pkg-config \
    mariadb-server libmariadb-dev \
    apache2 apache2-utils libapache2-mod-wsgi-py3 \
    redis >> /tmp/install.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

############ 
# Secure MySQL installation non-interactively
#
echo -n -e "[\033[90mINFO\033[0m] MYSQL SECURE INSTALL ............................ " | tee -a /tmp/install.log
sudo mysql >> /tmp/install.log 2>&1 <<-EOSQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PWD}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
EOSQL
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

############ 
# Create the DeepHunter database and user
#
echo -n -e "[\033[90mINFO\033[0m] CREATE DATABASE ................................. " | tee -a /tmp/install.log
mysql -u root -p"$MYSQL_ROOT_PWD" >> /tmp/install.log 2>&1 <<-EOSQL
CREATE DATABASE deephunter;
CREATE USER 'deephunter'@'localhost' IDENTIFIED BY '${MYSQL_DEEPHUNTER_PWD}';
GRANT ALL PRIVILEGES ON deephunter.* TO 'deephunter'@'localhost';
FLUSH PRIVILEGES;
EOSQL
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

############ 
# Download DeepHunter v2.5
#
echo -n -e "[\033[90mINFO\033[0m] DOWNLOADING DEEPHUNTER .......................... " | tee -a /tmp/install.log
cd /tmp/
wget -q https://github.com/sebastiendamaye/deephunter/archive/refs/tags/v2.5.tar.gz >> /tmp/install.log 2>&1
tar xzf v2.5.tar.gz -C "${APP_PATH}" --strip-components=1 >> /tmp/install.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

############ 
# Build the virtual environment
#
echo -n -e "[\033[90mINFO\033[0m] CREATING VIRTUAL ENVIRONMENT .................... " | tee -a /tmp/install.log
python3 -m venv $VENV_PATH >> /tmp/install.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

############ 
# Install Python dependencies
#
echo -n -e "[\033[90mINFO\033[0m] INSTALLING PYTHON DEPENDENCIES .................. " | tee -a /tmp/install.log
source $VENV_PATH/bin/activate
cd ${APP_PATH}
pip install -r requirements.txt >> /tmp/install.log 2>&1
deactivate
chmod -R 755 $VENV_PATH
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

############# 
# Make settings adjustments
#
echo -n -e "[\033[90mINFO\033[0m] PREPARING SETTINGS FILE ......................... " | tee -a /tmp/install.log
cd ${APP_PATH}/deephunter/
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
dos2unix -q settings.py >> /tmp/install.log 2>&1

echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log


#############
# Create initial database and load initial data
#
echo -n -e "[\033[90mINFO\033[0m] CREATING INITIAL DATABASE ....................... " | tee -a /tmp/install.log
# First temporarily disable signals.
sed -i 's/import qm.signals/pass #import qm.signals/' ${APP_PATH}/qm/apps.py

# create the initial database schema:
source $VENV_PATH/bin/activate
cd ${APP_PATH}
./manage.py makemigrations qm >> /tmp/install.log 2>&1
./manage.py makemigrations extensions >> /tmp/install.log 2>&1
./manage.py makemigrations reports >> /tmp/install.log 2>&1
./manage.py makemigrations connectors >> /tmp/install.log 2>&1
./manage.py makemigrations repos >> /tmp/install.log 2>&1
./manage.py makemigrations notifications >> /tmp/install.log 2>&1
./manage.py makemigrations dashboard >> /tmp/install.log 2>&1
./manage.py makemigrations config >> /tmp/install.log 2>&1
./manage.py makemigrations >> /tmp/install.log 2>&1
./manage.py migrate >> /tmp/install.log 2>&1

echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

#############
# Create Django super user (prerequisite before loading initial data to get at least 1 user to link to)
#
echo -n -e "[\033[90mINFO\033[0m] CREATING DJANGO ADMIN USER ...................... " | tee -a /tmp/install.log
DJANGO_SUPERUSER_USERNAME=admin \
DJANGO_SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PWD} \
DJANGO_SUPERUSER_EMAIL=admin@localhost \
python manage.py createsuperuser --no-input >> /tmp/install.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

echo -n -e "[\033[90mINFO\033[0m] LOADING INITIAL DATA ............................ " | tee -a /tmp/install.log
# load initial data from fixtures
./manage.py loaddata install/fixtures/v2.5/qm_country.json >> /tmp/install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_threatactor.json >> /tmp/install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_threatname.json >> /tmp/install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_vulnerability.json >> /tmp/install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_mitretactic.json >> /tmp/install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_mitretechnique.json >> /tmp/install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_tag.json >> /tmp/install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_category.json >> /tmp/install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_targetos.json >> /tmp/install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_savedsearch.json >> /tmp/install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/config.json >> /tmp/install.log 2>&1

# connector fixture has been updated (bug fix)
sed -i 's|"visible_in_analytics": true|"domain": "analytics"|' install/fixtures/v2.5/connectors.json
sed -i 's|"visible_in_analytics": false|"domain": ""|' install/fixtures/v2.5/connectors.json
./manage.py loaddata install/fixtures/v2.5/connectors.json >> /tmp/install.log 2>&1

./manage.py loaddata install/fixtures/v2.5/qm_analytic.json >> /tmp/install.log 2>&1

deactivate
# Restore signals:
sed -i 's/pass #import qm.signals/import qm.signals/' ${APP_PATH}/qm/apps.py
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

echo -n -e "[\033[90mINFO\033[0m] FIXING PERMISSIONS .............................. " | tee -a /tmp/install.log
# Fix permissions
chmod -R 775 ${APP_PATH} >> /tmp/install.log 2>&1
touch ${APP_PATH}/static/mitre.json >> /tmp/install.log 2>&1
chmod 666 ${APP_PATH}/static/mitre.json >> /tmp/install.log 2>&1
chmod 664 $APP_PATH/static/VERSION* >> /tmp/install.log 2>&1
chmod 664 $APP_PATH/static/commit_id.txt >> /tmp/install.log 2>&1
chown -R $USER_GROUP $VENV_PATH >> /tmp/install.log 2>&1
chmod -R 755 $VENV_PATH >> /tmp/install.log 2>&1
sudo chown :$SERVER_USER $APP_PATH/deephunter/wsgi.py >> /tmp/install.log 2>&1
sudo chown -R :$SERVER_USER $APP_PATH/plugins/ >> /tmp/install.log 2>&1
sudo chmod g+s $APP_PATH/plugins/ >> /tmp/install.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log


#############
# Configure Apache
#
echo -n -e "[\033[90mINFO\033[0m] CONFIGURING APACHE2 ............................. " | tee -a /tmp/install.log
sudo a2enmod headers >> /tmp/install.log 2>&1

# Create a self-signed certificate
cd ${APP_PATH}/install/scripts/common/
chmod +x ./generate_deephunter_self_cert.sh >> /tmp/install.log 2>&1
./generate_deephunter_self_cert.sh deephunter.localtest.me >> /tmp/install.log 2>&1
sudo a2enmod ssl >> /tmp/install.log 2>&1

# improve your encryption by creating a strong DH Group, and enable Perfect Forward Secrecy:
sudo cp ${APP_PATH}/install/etc/apache2/conf-available/ssl-params.conf /etc/apache2/conf-available/
sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048 >> /tmp/install.log 2>&1
sudo a2enconf ssl-params >> /tmp/install.log 2>&1

# Enable site in HTTPS
sed -i "s|/data/deephunter|${APP_PATH}|" ${APP_PATH}/install/etc/apache2/sites-available/deephunter-ssl.conf
sudo cp ${APP_PATH}/install/etc/apache2/sites-available/deephunter-ssl.conf /etc/apache2/sites-available/
sudo a2ensite deephunter-ssl >> /tmp/install.log 2>&1

echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

#############
# Install celery
#
echo -n -e "[\033[90mINFO\033[0m] CONFIGURING CELERY .............................. " | tee -a /tmp/install.log

sed -i "s|/data/venv|${VENV_PATH}|" ${APP_PATH}/install/etc/default/celery
sudo cp ${APP_PATH}/install/etc/default/celery /etc/default/celery

# On Ubuntu Server, it seems that the /var/run/ directory is purged at each reboot.
# To make sure the celery subdirectory is recreated at each boot, you can create the following file
echo 'd /var/run/celery 0755 celery celery' | sudo tee /etc/tmpfiles.d/celery.conf >> /tmp/install.log 2>&1

# create the celery user and group.
sudo groupadd celery
sudo useradd -g celery celery

# Create the directories and fix permissions:
sudo mkdir /var/run/celery/
sudo chown celery:celery /var/run/celery/
sudo mkdir /var/log/celery/
sudo chown celery:celery /var/log/celery/

# To start the Celery service automatically, you may want to create a file in /etc/systemd/system/celery.service as follows:
sudo cp ${APP_PATH}/install/etc/systemd/system/celery.service /etc/systemd/system/celery.service

# Reload services and enable them:
sudo systemctl daemon-reload >> /tmp/install.log 2>&1
sudo systemctl enable celery.service >> /tmp/install.log 2>&1
sudo systemctl start celery.service >> /tmp/install.log 2>&1

echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

# Restart services to apply all changes
echo -n -e "[\033[90mINFO\033[0m] RESTARTING SERVICES ............................. " | tee -a /tmp/install.log
sudo systemctl restart apache2 >> /tmp/install.log 2>&1
sudo systemctl restart redis >> /tmp/install.log 2>&1

echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/install.log

#############
# Installation complete
#
echo "INSTALLATION COMPLETE" >> /tmp/install.log
echo
echo "+===========================================================================+"
echo "|                      *** INSTALLATION COMPLETE ***                        |"
echo "+===========================================================================+"
echo 
echo "  You can now access DeepHunter at https://${IP_ADDRESS}/"
echo 
echo "  Below are the passwords that have been auto-generated by the installer:"
echo "  - MySQL 'root' password: ${MYSQL_ROOT_PWD}"
echo "  - MySQL 'deephunter' password: ${MYSQL_DEEPHUNTER_PWD}"
echo "  - Django 'admin' password: ${DJANGO_SUPERUSER_PWD}"
echo 
echo "  Go to Admin > Settings > Connectors and update the settings as needed."
echo 
echo "  Post-installation recommendations:"
echo "  - Change passwords."
echo "  - Set DEBUG to False in your settings.py file."
echo "  - Review settings and fine tune the configuration."
echo "  - Generate a valid certificate."
echo "  - Generate a PGP key for encrypted backups."
echo 
echo "============================================================================="
echo
