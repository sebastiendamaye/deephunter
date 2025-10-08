#!/bin/bash
# DeepHunter installer script
# Version 2.5
# This script will install DeepHunter v2.5 on a Ubuntu Server, with MariaDB as database, and Apache as web server with WSGI and a self-signed certificate.
set -euo pipefail
trap 'echo "ERROR: Script failed at line $LINENO. Check install.log."; exit 1' ERR

### Modify these variables as needed
#
export APP_PATH="/data/deephunter"
export VENV_PATH="/data/venv"
export TEMP_FOLDER="/data/tmp"

### Don't modify anything below this line unless you know what you're doing
#
#
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

echo > install.log

############ 
# Generate random passwords
#
echo -n -e "[\033[90mINFO\033[0m] GENERATING PASSWORDS ............................ "
echo "GENERATING PASSWORDS ............................" >> install.log
# Generate random passwords (32 characters, alphanumeric only)
MYSQL_ROOT_PWD="$(openssl rand -base64 32 | tr -d '=+/ ' | cut -c1-32)"
MYSQL_DEEPHUNTER_PWD="$(openssl rand -base64 32 | tr -d '=+/ ' | cut -c1-32)"
DJANGO_SUPERUSER_PWD="$(openssl rand -base64 32 | tr -d '=+/ ' | cut -c1-32)"
echo -e "[\033[32mdone\033[0m]" | tee -a install.log

############ 
# Remove any existing installation
# Create application directory
#
echo -n -e "[\033[90mINFO\033[0m] CREATING DIRECTORIES ............................ "
echo "CREATING DIRECTORIES ............................" >> install.log
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
echo -e "[\033[32mdone\033[0m]" | tee -a install.log

############ 
# Update and install dependencies
#
echo -n -e "[\033[90mINFO\033[0m] INSTALLING REQUIRED PACKAGES .................... "
echo "INSTALLING REQUIRED PACKAGES .................... " >> install.log
sudo apt-get update >> install.log 2>&1
sudo apt-get install -y git wget gnupg dos2unix \
    python3-venv python3-wheel python3-dev \
    build-essential pkg-config \
    mariadb-server libmariadb-dev \
    apache2 apache2-utils libapache2-mod-wsgi-py3 \
    redis >> install.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a install.log

############ 
# Secure MySQL installation non-interactively
#
echo -n -e "[\033[90mINFO\033[0m] MYSQL SECURE INSTALL ............................ "
echo "MYSQL SECURE INSTALL ............................" >> install.log
sudo mysql >> install.log 2>&1 <<-EOSQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PWD}';
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
EOSQL
echo -e "[\033[32mdone\033[0m]" | tee -a install.log

############ 
# Create the DeepHunter database and user
#
echo -n -e "[\033[90mINFO\033[0m] CREATE DATABASE ................................. "
echo "CREATE DATABASE ................................." >> install.log
mysql -u root -p"$MYSQL_ROOT_PWD" >> install.log 2>&1 <<-EOSQL
CREATE DATABASE deephunter;
CREATE USER 'deephunter'@'localhost' IDENTIFIED BY '${MYSQL_DEEPHUNTER_PWD}';
GRANT ALL PRIVILEGES ON deephunter.* TO 'deephunter'@'localhost';
FLUSH PRIVILEGES;
EOSQL
echo -e "[\033[32mdone\033[0m]" | tee -a install.log

############ 
# Download DeepHunter v2.5
#
echo -n -e "[\033[90mINFO\033[0m] DOWNLOADING DEEPHUNTER .......................... "
echo "DOWNLOADING DEEPHUNTER .......................... " >> install.log
cd /tmp/
wget -q https://github.com/sebastiendamaye/deephunter/archive/refs/tags/v2.5.tar.gz >> install.log 2>&1
tar xzf v2.5.tar.gz -C "${APP_PATH}" --strip-components=1 >> install.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a install.log

############ 
# Build the virtual environment
#
echo -n -e "[\033[90mINFO\033[0m] CREATING VIRTUAL ENVIRONMENT .................... "
echo "CREATING VIRTUAL ENVIRONMENT .................... " >> install.log
python3 -m venv $VENV_PATH >> install.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a install.log

############ 
# Install Python dependencies
#
echo -n -e "[\033[90mINFO\033[0m] INSTALLING PYTHON DEPENDENCIES .................. "
echo "INSTALLING PYTHON DEPENDENCIES .................. " >> install.log
source $VENV_PATH/bin/activate
cd ${APP_PATH}
pip install -r requirements.txt -q >> install.log 2>&1
deactivate
chmod -R 755 $VENV_PATH
echo -e "[\033[32mdone\033[0m]" | tee -a install.log

############# 
# Make settings adjustments
#
echo -n -e "[\033[90mINFO\033[0m] PREPARING SETTINGS FILE ......................... "
echo "PREPARING SETTINGS FILE ......................... " >> install.log
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
dos2unix -q settings.py >> install.log 2>&1

echo -e "[\033[32mdone\033[0m]" | tee -a install.log


#############
# Create initial database and load initial data
#
echo -n -e "[\033[90mINFO\033[0m] CREATING INITIAL DATABASE ....................... "
echo "CREATING INITIAL DATABASE ....................... " >> install.log
# First temporarily disable signals.
sed -i 's/import qm.signals/pass #import qm.signals/' ${APP_PATH}/qm/apps.py

# create the initial database schema:
source $VENV_PATH/bin/activate
cd ${APP_PATH}
./manage.py makemigrations qm >> install.log 2>&1
./manage.py makemigrations extensions >> install.log 2>&1
./manage.py makemigrations reports >> install.log 2>&1
./manage.py makemigrations connectors >> install.log 2>&1
./manage.py makemigrations repos >> install.log 2>&1
./manage.py makemigrations notifications >> install.log 2>&1
./manage.py makemigrations dashboard >> install.log 2>&1
./manage.py makemigrations config >> install.log 2>&1
./manage.py makemigrations >> install.log 2>&1
./manage.py migrate >> install.log 2>&1

echo -e "[\033[32mdone\033[0m]" | tee -a install.log

#############
# Create Django super user (prerequisite before loading initial data to get at least 1 user to link to)
#
echo -n -e "[\033[90mINFO\033[0m] CREATING DJANGO ADMIN USER ...................... "
echo "CREATING DJANGO ADMIN USER ...................... " >> install.log
DJANGO_SUPERUSER_USERNAME=admin \
DJANGO_SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PWD} \
DJANGO_SUPERUSER_EMAIL=admin@localhost \
python manage.py createsuperuser --no-input >> install.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a install.log

echo -n -e "[\033[90mINFO\033[0m] LOADING INITIAL DATA ............................ "
echo "LOADING INITIAL DATA ............................ " >> install.log
# load initial data from fixtures
./manage.py loaddata install/fixtures/v2.5/qm_country.json >> install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_threatactor.json >> install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_threatname.json >> install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_vulnerability.json >> install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_mitretactic.json >> install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_mitretechnique.json >> install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_tag.json >> install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_category.json >> install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_targetos.json >> install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/qm_savedsearch.json >> install.log 2>&1
./manage.py loaddata install/fixtures/v2.5/config.json >> install.log 2>&1

# connector fixture has been updated (bug fix)
sed -i 's|"visible_in_analytics": true|"domain": "analytics"|' install/fixtures/v2.5/connectors.json
sed -i 's|"visible_in_analytics": false|"domain": ""|' install/fixtures/v2.5/connectors.json
./manage.py loaddata install/fixtures/v2.5/connectors.json >> install.log 2>&1

./manage.py loaddata install/fixtures/v2.5/qm_analytic.json >> install.log 2>&1

deactivate
# Restore signals:
sed -i 's/pass #import qm.signals/import qm.signals/' ${APP_PATH}/qm/apps.py
echo -e "[\033[32mdone\033[0m]" | tee -a install.log

echo -n -e "[\033[90mINFO\033[0m] FIXING PERMISSIONS .............................. "
echo "FIXING PERMISSIONS .............................. " >> install.log
# Fix permissions
chmod -R 755 ${APP_PATH}
touch ${APP_PATH}/static/mitre.json
chmod 666 ${APP_PATH}/static/mitre.json
echo -e "[\033[32mdone\033[0m]" | tee -a install.log

#############
# Configure Apache
#
echo -n -e "[\033[90mINFO\033[0m] CONFIGURING APACHE2 ............................. "
echo "CONFIGURING APACHE2 ............................. " >> install.log
sudo a2enmod headers >> install.log 2>&1

# Create a self-signed certificate
cd ${APP_PATH}/install/scripts/common/
chmod +x ./generate_deephunter_self_cert.sh >> install.log 2>&1
./generate_deephunter_self_cert.sh deephunter.localtest.me >> install.log 2>&1
sudo a2enmod ssl >> install.log 2>&1

# improve your encryption by creating a strong DH Group, and enable Perfect Forward Secrecy:
sudo cp ${APP_PATH}/install/etc/apache2/conf-available/ssl-params.conf /etc/apache2/conf-available/
sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048 >> install.log 2>&1
sudo a2enconf ssl-params >> install.log 2>&1

# Enable site in HTTPS
sed -i "s|/data/deephunter|${APP_PATH}|" ${APP_PATH}/install/etc/apache2/sites-available/deephunter-ssl.conf
sudo cp ${APP_PATH}/install/etc/apache2/sites-available/deephunter-ssl.conf /etc/apache2/sites-available/
sudo a2ensite deephunter-ssl >> install.log 2>&1

echo -e "[\033[32mdone\033[0m]" | tee -a install.log

#############
# Install celery
#
echo -n -e "[\033[90mINFO\033[0m] CONFIGURING CELERY .............................. "
echo "CONFIGURING CELERY .............................. " >> install.log

sed -i "s|/data/venv|${VENV_PATH}|" ${APP_PATH}/install/etc/default/celery
sudo cp ${APP_PATH}/install/etc/default/celery /etc/default/celery

# On Ubuntu Server, it seems that the /var/run/ directory is purged at each reboot.
# To make sure the celery subdirectory is recreated at each boot, you can create the following file
echo 'd /var/run/celery 0755 celery celery' | sudo tee /etc/tmpfiles.d/celery.conf > install.log 2>&1

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
sudo systemctl daemon-reload >> install.log 2>&1
sudo systemctl enable celery.service >> install.log 2>&1
sudo systemctl start celery.service >> install.log 2>&1

echo -e "[\033[32mdone\033[0m]" | tee -a install.log

# Restart services to apply all changes
echo -n -e "[\033[90mINFO\033[0m] RESTARTING SERVICES ............................. "
echo "RESTARTING SERVICES ............................. " >> install.log
sudo systemctl restart apache2 >> install.log 2>&1
sudo systemctl restart redis >> install.log 2>&1

echo -e "[\033[32mdone\033[0m]" | tee -a install.log

#############
# Installation complete
#
echo "INSTALLATION COMPLETE" >> install.log
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
