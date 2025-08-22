#!/bin/bash

######################################
# FUNCTIONS
#

# Function to extract keys from a settings.py file
extract_keys() {
    grep -oP "^\s*\K\w+" "$1"
}
# Function that checks if a variable is empty
check_empty() {
    if [ -z "$2" ]; then
		echo -e "[\033[31mERROR\033[0m] Unable to extract $1 from your settings file."
		exit 1
    fi
}

# Banner
echo ''
echo '  _____  ______ ______ _____  _    _ _    _ _   _ _______ ______ _____  '
echo ' |  __ \|  ____|  ____|  __ \| |  | | |  | | \ | |__   __|  ____|  __ \ '
echo ' | |  | | |__  | |__  | |__) | |__| | |  | |  \| |  | |  | |__  | |__) |'
echo ' | |  | |  __| |  __| |  ___/|  __  | |  | | . ` |  | |  |  __| |  _  / '
echo ' | |__| | |____| |____| |    | |  | | |__| | |\  |  | |  | |____| | \ \ '
echo ' |_____/|______|______|_|    |_|  |_|\____/|_| \_|  |_|  |______|_|  \_\'
echo ''
echo '                   *** DEEPHUNTER UPGRADE SCRIPT ***'
echo ''


######################################
# PREREQUISITES
#

error=0
echo -e "[\033[90mINFO\033[0m] CHECKING PREREQUISITES"

# Checking that sudo is installed
if which sudo > /dev/null 2>&1; then
	echo -e "  sudo ................................................. [\033[32mfound\033[0m]"
else
	echo -e "  sudo ................................................. [\033[31mmissing\033[0m]"
	error=1
fi
# Checking that curl is installed
if which curl > /dev/null 2>&1; then
	echo -e "  curl ................................................. [\033[32mfound\033[0m]"
else
	echo -e "  curl ................................................. [\033[31mmissing\033[0m]"
	error=1
fi
# Checking that wget is installed
if which wget > /dev/null 2>&1; then
	echo -e "  wget ................................................. [\033[32mfound\033[0m]"
else
	echo -e "  wget ................................................. [\033[31mmissing\033[0m]"
	error=1
fi
# Checking that git is installed
if which git > /dev/null 2>&1; then
	echo -e "  git .................................................. [\033[32mfound\033[0m]"
else
	echo -e "  git .................................................. [\033[31mmissing\033[0m]"
	error=1
fi
# Checking that tar is installed
if which tar > /dev/null 2>&1; then
	echo -e "  tar .................................................. [\033[32mfound\033[0m]"
else
	echo -e "  tar .................................................. [\033[31mmissing\033[0m]"
	error=1
fi
# Checking that user has sudo
user_groups=$(groups $(whoami))
if echo "$user_groups" | grep -qw "sudo" || echo "$user_groups" | grep -qw "admin"; then
	echo -e "  User has sudo access ................................. [\033[32mOK\033[0m]"
else
	echo -e "  User has sudo access ................................. [\033[31mfailed\033[0m]"
	error=1
fi

# Exit on error
if [ $error = 1 ]; then
	echo -e "[\033[31mERROR\033[0m] The upgrade script is missing mandatory dependencies. Install these packages first."
	exit 1
fi

######################################
# GET SETTINGS
#

# Search for the settings file on disk
# (assuming it is in the following relative path ./deephunter/deephunter/settings.py)
echo -n -e "[\033[90mINFO\033[0m] LOOKING FOR THE SETTINGS.PY FILE ................ "
SETTINGS_PATHS=$(find / -type f -path "*/deephunter/deephunter/*" -name "settings.py" 2>/dev/null)
if [ -z "${SETTINGS_PATHS}" ]; then
	echo -e "[\033[31mnot found\033[0m]"
	exit 1
else
	echo -e "[\033[32mfound\033[0m]"
fi

# Count the number of settings.py files found
NUM_PATHS=$(echo "$SETTINGS_PATHS" | wc -l)

# If only one settings.py found...
if [ "$NUM_PATHS" -eq 1 ]; then
	# Confirm settings path is correct
	while true; do
		echo -n -e "[\033[34mCONFIRM\033[0m] "
		read -p "Settings file found in \"$SETTINGS_PATHS\". Is it correct (Y/n)? " response
		# If no input is provided (just Enter), set response to 'Y'
		response=${response:-Y}
		# Convert the response to uppercase to handle both 'y' and 'Y'
		response=$(echo "$response" | tr '[:lower:]' '[:upper:]')

		if [[ "$response" == "Y" || "$response" == "YES" ]]; then
			SETTINGS_PATH=$SETTINGS_PATHS
			break
		elif [[ "$response" == "N" || "$response" == "NO" ]]; then
			exit 1
		else
			echo "Invalid response. Please enter Y, YES, N, or NO."
		fi
	done
fi

# If multiple files are found, prompt the user to select one
if [ "$NUM_PATHS" -gt 1 ]; then
    # Display the paths with a number
	echo -e "[\033[34mCONFIRM\033[0m] Please select the correct settings.py file by number"
    PS3="Selection: "
    select SETTINGS_PATH in $SETTINGS_PATHS; do
        if [ -n "$SETTINGS_PATH" ]; then
            break
        else
            echo "Invalid selection. Please try again."
        fi
    done
fi

# Extract variables from settings.py
APP_PATH=$(dirname "$SETTINGS_PATH" | sed 's:/deephunter$::')
# Remove all comments from settings and save a copy in tmp
# This is a necessary prerequisite in order to avoid duplicates during extraction
grep -v '^#' $APP_PATH/deephunter/settings.py > /tmp/settings.py
TEMP_FOLDER=$(grep -oP 'TEMP_FOLDER\s?=\s?"\K[^"]+' /tmp/settings.py)
check_empty "TEMP_FOLDER" "$TEMP_FOLDER"
VENV_PATH=$(grep -oP 'VENV_PATH\s?=\s?"\K[^"]+' /tmp/settings.py)
check_empty "VENV_PATH" "$VENV_PATH"
UPDATE_ON=$(grep -oP 'UPDATE_ON\s?=\s?"\K[^"]+' /tmp/settings.py)
check_empty "UPDATE_ON" "$UPDATE_ON"
USER=$(grep -oP 'USER_GROUP\s?=\s?"\K[^"]+' /tmp/settings.py)
check_empty "USER" "$USER"
GITHUB_URL=$(grep -oP 'GITHUB_URL\s?=\s?"\K[^"]+' /tmp/settings.py)
check_empty "GITHUB_URL" "$GITHUB_URL"
# List of django apps for migrations
APPS=(qm extensions reports connectors repos notifications)


######################################
# DOWNLOAD NEW VERSION (RELEASE OR COMMIT)
#

# Downloading new version
echo -n -e "[\033[90mINFO\033[0m] DOWNLOADING NEW VERSION OF DEEPHUNTER ........... "
cd /tmp
rm -fR deephunter*
if [ $UPDATE_ON = "release" ]; then
	response=$(curl -s "https://api.github.com/repos/sebastiendamaye/deephunter/releases/latest")
	url=$(echo $response | grep -o '"tarball_url": *"[^"]*"' | sed 's/"tarball_url": "//' | sed 's/"$//')
	wget -q -O deephunter.tar.gz $url
	mkdir deephunter
	tar xzf deephunter.tar.gz -C deephunter --strip-components=1
else
	rm -fR d
	mkdir d
	cd d
	git clone -q $GITHUB_URL
	cd /tmp
	mv d/deephunter .
	rm -fR d
fi

echo -e "[\033[32mcomplete\033[0m]"


######################################
# CHECK SETTINGS CONSISTENCY
#

# Checking settings.py consistency (presence of all keys)
echo -n -e "[\033[90mINFO\033[0m] CHECKING SETTINGS FILE CONSISTENCY .............. "

# Extract keys from the local and remote settings.py files
LOCAL_KEYS=$(extract_keys /tmp/settings.py)
NEW_KEYS=$(extract_keys "/tmp/deephunter/deephunter/settings.example.py")

# Compare the sets of keys (sorted to handle order) and check consistency
if diff <(echo "$LOCAL_KEYS" | sort) <(echo "$NEW_KEYS" | sort) > /dev/null; then
    echo -e "[\033[32mOK\033[0m]"
else
    echo -e "[\033[31mfailed\033[0m]"
    echo -e "[\033[31mERROR\033[0m] There are likely missing variables in your current settings.py file."
    # Show the differences between the local and new settings
    diff <(echo "$LOCAL_KEYS" | sort) <(echo "$NEW_KEYS" | sort)
    echo -e "[\033[90mINFO\033[0m] Please use a text editor to add the missing element(s). You can for example use 'nano -c /data/deephunter/deephunter/settings.py' to edit it."
    exit 1
fi

######################################
# UPGRADE
#

# Stop services
echo -n -e "[\033[90mINFO\033[0m] STOPPING SERVICES ............................... "
sudo systemctl stop apache2
sudo systemctl stop celery
sudo systemctl stop redis-server
echo -e "[\033[32mdone\033[0m]"

# Backup DB (encrypted. Use the same as DB backup in crontab. Backup will be located in the same folder)
echo -n -e "[\033[90mINFO\033[0m] STARTING DB BACKUP .............................. "
source $VENV_PATH/bin/activate
cd $APP_PATH
$VENV_PATH/bin/python3 manage.py dbbackup --encrypt
#leave virtual env
deactivate
echo -e "[\033[32mdone\033[0m]"

# Backup source
echo -n -e "[\033[90mINFO\033[0m] STARTING APP BACKUP ............................. "
rm -fR $TEMP_FOLDER/deephunter
mkdir -p $TEMP_FOLDER
cp -R $APP_PATH $TEMP_FOLDER
echo -e "[\033[32mdone\033[0m]"

# Installation of the update
while true; do
	echo -n -e "[\033[34mCONFIRM\033[0m] "
	read -p "Proceed with installation of the new version (Y/n)? " response
	# If no input is provided (just Enter), set response to 'Y'
	response=${response:-Y}
	# Convert the response to uppercase to handle both 'y' and 'Y'
	response=$(echo "$response" | tr '[:lower:]' '[:upper:]')
	# Check the response
	if [[ "$response" == "Y" || "$response" == "YES" ]]; then
		break
	elif [[ "$response" == "N" || "$response" == "NO" ]]; then
		exit 0
	else
		echo "Invalid response. Please enter Y, YES, N, or NO."
	fi
done

echo -n -e "[\033[90mINFO\033[0m] INSTALLING UPDATE ............................... "
rm -fR $APP_PATH
cp -R /tmp/deephunter $APP_PATH
echo -e "[\033[32mdone\033[0m]"

echo -n -e "[\033[90mINFO\033[0m] RESTORING MIGRATIONS FOLDERS AND SETTINGS ....... "
for app in ${APPS[@]}
do
	cp -R $TEMP_FOLDER/deephunter/$app/migrations/ $APP_PATH/$app/ 2>/dev/null
done
# Restore settings
cp $TEMP_FOLDER/deephunter/deephunter/settings.py $APP_PATH/deephunter/
echo -e "[\033[32mdone\033[0m]"

# DB Migrations
while true; do
	echo -n -e "[\033[34mCONFIRM\033[0m] "
	read -p "Proceed with DB migrations (Y/n)? " response
	# If no input is provided (just Enter), set response to 'Y'
	response=${response:-Y}
	# Convert the response to uppercase to handle both 'y' and 'Y'
	response=$(echo "$response" | tr '[:lower:]' '[:upper:]')
	# Check the response
	if [[ "$response" == "Y" || "$response" == "YES" ]]; then
		break
	elif [[ "$response" == "N" || "$response" == "NO" ]]; then
		exit 0
	else
		echo "Invalid response. Please enter Y, YES, N, or NO."
	fi
done

echo -e "[\033[90mINFO\033[0m] PERFORMING DB MIGRATIONS ........................ "
source $VENV_PATH/bin/activate
cd $APP_PATH/
for app in ${APPS[@]}
do
	./manage.py makemigrations $app
done

./manage.py migrate
# Leave python virtual env
deactivate
echo -e "[\033[90mINFO\033[0m] DB MIGRATIONS COMPLETE"


# Restore permissions
echo -n -e "[\033[90mINFO\033[0m] RESTORING PERMISSIONS ........................... "
chmod -R 775 $APP_PATH
touch $APP_PATH/static/mitre.json
chmod 666 $APP_PATH/static/mitre.json
chmod 664 $APP_PATH/static/VERSION*
chmod 664 $APP_PATH/static/commit_id.txt
chown -R $USER $VENV_PATH
chmod -R 775 $VENV_PATH
echo -e "[\033[32mdone\033[0m]"

# Restart apache2
echo -n -e "[\033[90mINFO\033[0m] RESTARTING SERVICES ............................. "
sudo systemctl start apache2
sudo systemctl restart redis-server
sudo systemctl restart celery
sudo systemctl restart cron
echo -e "[\033[32mdone\033[0m]"

# cleaning /tmp
echo -n -e "[\033[90mINFO\033[0m] CLEANING /TMP DIR ............................... "
rm -fR /tmp/deephunter* /tmp/settings.py
echo -e "[\033[32mdone\033[0m]"

echo ""
echo "****************************************************************************************"
echo "* Your DATA_TEMP folder has not been removed and keeps a copy of your old installation *"
echo "* If the update went well, you should manually remove any content in this directory.   *"
echo "****************************************************************************************"
echo ""

echo -e "[\033[90mINFO\033[0m] UPGRADE COMPLETE"
