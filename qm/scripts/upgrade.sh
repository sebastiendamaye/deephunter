#!/bin/bash
# DeepHunter upgrade script
# This script will upgrade DeepHunter to the latest version (commit or release, depending on your settings)
set -euo pipefail
trap 'echo "ERROR: Script failed at line $LINENO. Check /tmp/upgrade.log."; sed -n "$LINENO p" /tmp/upgrade.log; exit 1' ERR

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
		echo -e "[\033[31mERROR\033[0m] Unable to extract $1 from your settings file." | tee -a /tmp/upgrade.log
		exit 1
    fi
}

self_update() {

	echo -n -e "[\033[90mINFO\033[0m] CHECKING SCRIPT VERSION ......................... " | tee -a /tmp/upgrade.log
	REMOTE_SCRIPT="https://raw.githubusercontent.com/sebastiendamaye/deephunter/main/qm/scripts/upgrade.sh"

	LOCAL_HASH=$(sha1sum $0 | awk '{print $1}')
	REMOTE_HASH=$(curl -s $REMOTE_SCRIPT | sha1sum | awk '{print $1}')

    if [ "$REMOTE_HASH" != "$LOCAL_HASH" ]; then
		echo -e "[\033[31mupdate available\033[0m]" | tee -a /tmp/upgrade.log

		# Installation of the update
		while true; do
			echo -n -e "[\033[34mCONFIRM\033[0m] "
			read -p "Update the script to the latest version (Y/n)? " response
			# If no input is provided (just Enter), set response to 'Y'
			response=${response:-Y}
			# Convert the response to uppercase to handle both 'y' and 'Y'
			response=$(echo "$response" | tr '[:lower:]' '[:upper:]')
			# Check the response
			if [[ "$response" == "Y" || "$response" == "YES" ]]; then
				tmpfile=$(mktemp)
				curl -s -o "$tmpfile" "$REMOTE_SCRIPT" >> /tmp/upgrade.log 2>&1
				if [ $? -ne 0 ]; then
					echo -e "[\033[31mERROR\033[0m] Failed to download new version." | tee -a /tmp/upgrade.log
					exit 1
				fi
				chmod +x "$tmpfile" >> /tmp/upgrade.log 2>&1
				dos2unix "$tmpfile" >> /tmp/upgrade.log 2>&1
				SCRIPT_PATH="$(realpath "$0")"
				mv "$tmpfile" "$SCRIPT_PATH" >> /tmp/upgrade.log 2>&1
				clear
				echo "Restarting script..." | tee -a /tmp/upgrade.log
				exec "$SCRIPT_PATH" "$@"
				exit 0
			elif [[ "$response" == "N" || "$response" == "NO" ]]; then
				break
			else
				echo "Invalid response. Please enter Y, YES, N, or NO."
			fi
		done
    else
		echo -e "[\033[32mup-to-date\033[0m]" | tee -a /tmp/upgrade.log
    fi
}

# Banner
echo ""
echo "   ____                  _   _             _            "
echo "  |  _ \  ___  ___ _ __ | | | |_   _ _ __ | |_ ___ _ __ "
echo "  | | | |/ _ \/ _ \ '_ \| |_| | | | | '_ \| __/ _ \ '__|"
echo "  | |_| |  __/  __/ |_) |  _  | |_| | | | | ||  __/ |   "
echo "  |____/ \___|\___| .__/|_| |_|\__,_|_| |_|\__\___|_|   "
echo "                  |_|                                   "
echo ""
echo "             *** DeepHunter Upgrade Script ***"
echo ""


######################################
# PREREQUISITES
#

# Create an empty log file
> /tmp/upgrade.log

# Checking prerequisites
echo -n -e "[\033[90mINFO\033[0m] CHECKING PREREQUISITES .......................... " | tee -a /tmp/upgrade.log

missing_tools=()
for tool in sudo curl wget git tar dos2unix; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        missing_tools+=("$tool")
    fi
done

if (( ${#missing_tools[@]} > 0 )); then
    echo
	echo -e "[\033[31mERROR\033[0m]" | tee -a /tmp/upgrade.log
	echo "Please install the missing tools: ${missing_tools[*]}" | tee -a /tmp/upgrade.log
    exit 1
fi

# Checking that user has sudo
user_groups=$(groups $(whoami))
if echo "$user_groups" | grep -qw "sudo" || echo "$user_groups" | grep -qw "admin"; then
	echo -e "[\033[32mOK\033[0m]" | tee -a /tmp/upgrade.log
else
	echo -e "[\033[31mERROR\033[0m]" | tee -a /tmp/upgrade.log
	echo -e "Please grant user sudo privileges." | tee -a /tmp/upgrade.log
	exit 1
fi

######################################
# CHECK IF NEW VERSION OF UPGRADE SCRIPT IS AVAILABLE
#
self_update

######################################
# GET SETTINGS
#

# Search for the settings file on disk
# (assuming it is in the following relative path ./deephunter/deephunter/settings.py)
echo -n -e "[\033[90mINFO\033[0m] LOOKING FOR THE SETTINGS.PY FILE ................ " | tee -a /tmp/upgrade.log
SETTINGS_PATHS=$(find / -type f -path "*/deephunter/deephunter/*" -name "settings.py" 2>/dev/null || true)
if [ -z "${SETTINGS_PATHS}" ]; then
	echo -e "[\033[31mnot found\033[0m]" | tee -a /tmp/upgrade.log
	exit 1
else
	echo -e "[\033[32mfound\033[0m]" | tee -a /tmp/upgrade.log
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

# Get the last commit id from the current installation
CURRENT_COMMIT=$(<$APP_PATH/static/commit_id.txt)

# Remove all comments from settings and save a copy in tmp
# This is a necessary prerequisite in order to avoid duplicates during extraction
grep -v '^#' $APP_PATH/deephunter/settings.py > /tmp/settings.py
TEMP_FOLDER=$(grep -oP 'TEMP_FOLDER\s?=\s?"\K[^"]+' /tmp/settings.py || true)
check_empty "TEMP_FOLDER" "$TEMP_FOLDER"
VENV_PATH=$(grep -oP 'VENV_PATH\s?=\s?"\K[^"]+' /tmp/settings.py || true)
check_empty "VENV_PATH" "$VENV_PATH"
UPDATE_ON=$(grep -oP 'UPDATE_ON\s?=\s?"\K[^"]+' /tmp/settings.py || true)
check_empty "UPDATE_ON" "$UPDATE_ON"
USER_GROUP=$(grep -oP 'USER_GROUP\s?=\s?"\K[^"]+' /tmp/settings.py || true)
check_empty "USER_GROUP" "$USER_GROUP"
SERVER_USER=$(grep -oP 'SERVER_USER\s?=\s?"\K[^"]+' /tmp/settings.py || true)
check_empty "SERVER_USER" "$SERVER_USER"
GITHUB_URL=$(grep -oP 'GITHUB_URL\s?=\s?"\K[^"]+' /tmp/settings.py || true)
check_empty "GITHUB_URL" "$GITHUB_URL"
DBBACKUP_GPG_RECIPIENT=$(grep -oP "DBBACKUP_GPG_RECIPIENT\s?=\s?'\K[^']+" /tmp/settings.py || true)
# List of django apps for migrations
APPS=(qm extensions reports connectors repos notifications dashboard config)


######################################
# DOWNLOAD NEW VERSION (RELEASE OR COMMIT)
#

# Downloading new version
echo -n -e "[\033[90mINFO\033[0m] DOWNLOADING NEW VERSION OF DEEPHUNTER ........... " | tee -a /tmp/upgrade.log
cd /tmp
rm -fR deephunter* >> /tmp/upgrade.log 2>&1
if [ $UPDATE_ON = "release" ]; then
	response=$(curl -s "https://api.github.com/repos/sebastiendamaye/deephunter/releases/latest")
	remote_version=$(echo $response | grep -oP '(?<="tag_name": ")[^"]+')
	local_version=$(cat $APP_PATH/static/VERSION 2>/dev/null)
	if [ "$remote_version" = "$local_version" ]; then
		echo -e "[\033[32mup-to-date\033[0m]" | tee -a /tmp/upgrade.log
		echo -e "[\033[90mINFO\033[0m] You are already running the latest version ($local_version). No update required." | tee -a /tmp/upgrade.log
		exit 0
	fi

	url=$(echo $response | grep -oP '(?<="tarball_url": ")[^"]+')
	wget -q -O deephunter.tar.gz $url >> /tmp/upgrade.log 2>&1
	mkdir deephunter >> /tmp/upgrade.log 2>&1
	tar xzf deephunter.tar.gz -C deephunter --strip-components=1 >> /tmp/upgrade.log 2>&1
else
	rm -fR d >> /tmp/upgrade.log 2>&1
	mkdir d >> /tmp/upgrade.log 2>&1
	cd d >> /tmp/upgrade.log 2>&1
	git clone -q $GITHUB_URL >> /tmp/upgrade.log 2>&1
	cd /tmp >> /tmp/upgrade.log 2>&1
	mv d/deephunter . >> /tmp/upgrade.log 2>&1
	rm -fR d >> /tmp/upgrade.log 2>&1
fi

echo -e "[\033[32mcomplete\033[0m]" | tee -a /tmp/upgrade.log


######################################
# CHECK SETTINGS CONSISTENCY
#

# Checking settings.py consistency (presence of all keys)
echo -n -e "[\033[90mINFO\033[0m] CHECKING SETTINGS FILE CONSISTENCY .............. " | tee -a /tmp/upgrade.log

# Extract keys from the local and remote settings.py files
LOCAL_KEYS=$(extract_keys /tmp/settings.py)
NEW_KEYS=$(extract_keys "/tmp/deephunter/deephunter/settings.example.py")

# Compare the sets of keys (sorted to handle order) and check consistency
if diff <(echo "$LOCAL_KEYS" | sort) <(echo "$NEW_KEYS" | sort) > /dev/null; then
    echo -e "[\033[32mOK\033[0m]" | tee -a /tmp/upgrade.log
else
    echo -e "[\033[31mfailed\033[0m]" | tee -a /tmp/upgrade.log
    echo -e "[\033[31mERROR\033[0m] There are likely missing variables in your current settings.py file." | tee -a /tmp/upgrade.log
    # Show the differences between the local and new settings
    diff <(echo "$LOCAL_KEYS" | sort) <(echo "$NEW_KEYS" | sort) | grep '^[<>]' || true | tee -a /tmp/upgrade.log
    echo -e "[\033[90mINFO\033[0m] Please use a text editor to add the missing element(s). You can for example use 'nano -c $APP_PATH/deephunter/settings.py' to edit it." | tee -a /tmp/upgrade.log
    exit 1
fi

######################################
# BACKUP
#

# Stop services
echo -n -e "[\033[90mINFO\033[0m] STOPPING SERVICES ............................... " | tee -a /tmp/upgrade.log
sudo systemctl stop apache2 >> /tmp/upgrade.log 2>&1
sudo systemctl stop celery >> /tmp/upgrade.log 2>&1
sudo systemctl stop redis-server >> /tmp/upgrade.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/upgrade.log

# Backup DB (encrypted. Use the same as DB backup in crontab. Backup will be located in the same folder)
echo -n -e "[\033[90mINFO\033[0m] STARTING DB BACKUP .............................. " | tee -a /tmp/upgrade.log
source $VENV_PATH/bin/activate >> /tmp/upgrade.log 2>&1
cd $APP_PATH >> /tmp/upgrade.log 2>&1
# If a GPG recipient is defined and the key is available, encrypt the backup, otherwise do not encrypt
if gpg --list-keys "$DBBACKUP_GPG_RECIPIENT" >/dev/null 2>&1; then
	$VENV_PATH/bin/python3 manage.py dbbackup --encrypt >> /tmp/upgrade.log 2>&1
else
	$VENV_PATH/bin/python3 manage.py dbbackup >> /tmp/upgrade.log 2>&1
fi
#leave virtual env
deactivate
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/upgrade.log

# Backup source
echo -n -e "[\033[90mINFO\033[0m] STARTING APP BACKUP ............................. " | tee -a /tmp/upgrade.log
rm -fR $TEMP_FOLDER/deephunter >> /tmp/upgrade.log 2>&1
mkdir -p $TEMP_FOLDER >> /tmp/upgrade.log 2>&1
cp -R $APP_PATH $TEMP_FOLDER >> /tmp/upgrade.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/upgrade.log

# Backup installed plugins
echo -n -e "[\033[90mINFO\033[0m] BACKUP INSTALLED PLUGINS ........................ " | tee -a /tmp/upgrade.log
installed_plugins=()
# List all .py files in the 'plugins' directory, excluding __init__.py
for file in $APP_PATH/plugins/*.py; do
    if [[ "$(basename "$file")" != "__init__.py" ]]; then
        installed_plugins+=("$(basename "$file")")
    fi
done
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/upgrade.log

######################################
# UPGRADE
#

# Installing pip dependencies in the virtual env
echo -n -e "[\033[90mINFO\033[0m] INSTALLING PIP DEPENDENCIES ..................... " | tee -a /tmp/upgrade.log
source $VENV_PATH/bin/activate >> /tmp/upgrade.log 2>&1
pip install -q -q --upgrade pip >> /tmp/upgrade.log 2>&1
pip install -q -q --upgrade -r /tmp/deephunter/requirements.txt >> /tmp/upgrade.log 2>&1
#leave virtual env
deactivate >> /tmp/upgrade.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/upgrade.log

# Installation of the update
while true; do
	echo -n -e "[\033[34mCONFIRM\033[0m] "
	read -p "Proceed with installation of the new version (Y/n)? " response | tee -a /tmp/upgrade.log
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

echo -n -e "[\033[90mINFO\033[0m] INSTALLING UPDATE ............................... " | tee -a /tmp/upgrade.log
# Sudo used here to be able to delete ""./plugins/__pycache__" that is owned by www-data)
sudo rm -fR $APP_PATH >> /tmp/upgrade.log 2>&1
cp -R /tmp/deephunter $APP_PATH >> /tmp/upgrade.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/upgrade.log

echo -n -e "[\033[90mINFO\033[0m] RESTORING MIGRATIONS FOLDERS AND SETTINGS ....... " | tee -a /tmp/upgrade.log
for app in ${APPS[@]}
do
	if [ -d $TEMP_FOLDER/deephunter/$app/migrations/ ]; then
		cp -R $TEMP_FOLDER/deephunter/$app/migrations/ $APP_PATH/$app/ >> /tmp/upgrade.log 2>&1
	fi
done
# Restore settings
cp $TEMP_FOLDER/deephunter/deephunter/settings.py $APP_PATH/deephunter/ >> /tmp/upgrade.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/upgrade.log

# DB Migrations
while true; do
	echo -n -e "[\033[34mCONFIRM\033[0m] "
	read -p "Proceed with DB migrations (Y/n)? " response | tee -a /tmp/upgrade.log
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

echo -n -e "[\033[90mINFO\033[0m] PERFORMING DB MIGRATIONS ........................ " | tee -a /tmp/upgrade.log
source $VENV_PATH/bin/activate >> /tmp/upgrade.log 2>&1
cd $APP_PATH/ >> /tmp/upgrade.log 2>&1
for app in ${APPS[@]}
do
	./manage.py makemigrations $app >> /tmp/upgrade.log 2>&1
done

./manage.py migrate >> /tmp/upgrade.log 2>&1
# Leave python virtual env
deactivate >> /tmp/upgrade.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/upgrade.log

# Restore installed plugins
echo -n -e "[\033[90mINFO\033[0m] RESTORING INSTALLED PLUGINS ..................... " | tee -a /tmp/upgrade.log
# Loop through the array and print the file names
for plugin in "${installed_plugins[@]}"; do
    # recreate the symlinks
    ln -s $APP_PATH/plugins/catalog/$plugin $APP_PATH/plugins/$plugin >> /tmp/upgrade.log 2>&1
done
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/upgrade.log

# Run all migrations scripts since last commit
echo -e "[\033[90mINFO\033[0m] RUNNING UPGRADE SCRIPTS ......................... " | tee -a /tmp/upgrade.log
source $VENV_PATH/bin/activate >> /tmp/upgrade.log 2>&1

echo "[DEBUG] Current commit: $CURRENT_COMMIT" >> /tmp/upgrade.log
git rev-list --reverse "${CURRENT_COMMIT}..HEAD" | while read COMMIT; do
    # For each commit, list added files in that commit
    git diff-tree --no-commit-id --name-status -r "$COMMIT" | while read STATUS FILE_PATH; do
        # Only consider added Python files in the target directory
        # Exclude blacklisted files (fr_160.py and fr_168.py) that have not been added since v2.4, they were just moved.
        if [[ "$STATUS" == "A" && "$FILE_PATH" == qm/scripts/upgrade/*.py 
            && "$FILE_PATH" != "qm/scripts/upgrade/fr_160.py" 
            && "$FILE_PATH" != "qm/scripts/upgrade/fr_168.py" ]]; then
            filename="${FILE_PATH##*/}"
            basename="${filename%.*}"
			echo -e "[\033[90mINFO\033[0m] Running upgrade script: $basename" | tee -a /tmp/upgrade.log
            python manage.py runscript "upgrade.$basename" >> /tmp/upgrade.log 2>&1
        fi
    done
done
deactivate >> /tmp/upgrade.log 2>&1
echo -e "[\033[90mINFO\033[0m] Upgrade scripts complete" | tee -a /tmp/upgrade.log

# Restore permissions
echo -n -e "[\033[90mINFO\033[0m] RESTORING PERMISSIONS ........................... " | tee -a /tmp/upgrade.log
chmod -R 775 $APP_PATH >> /tmp/upgrade.log 2>&1
touch $APP_PATH/static/mitre.json >> /tmp/upgrade.log 2>&1
chmod 666 $APP_PATH/static/mitre.json >> /tmp/upgrade.log 2>&1
chmod 664 $APP_PATH/static/VERSION* >> /tmp/upgrade.log 2>&1
chmod 664 $APP_PATH/static/commit_id.txt >> /tmp/upgrade.log 2>&1
chown -R $USER_GROUP $VENV_PATH >> /tmp/upgrade.log 2>&1
chmod -R 775 $VENV_PATH >> /tmp/upgrade.log 2>&1
sudo chown :$SERVER_USER $APP_PATH/deephunter/wsgi.py >> /tmp/upgrade.log 2>&1
sudo chown -R :$SERVER_USER $APP_PATH/plugins/ >> /tmp/upgrade.log 2>&1
sudo chmod g+s $APP_PATH/plugins/ >> /tmp/upgrade.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/upgrade.log

# Restart apache2
echo -n -e "[\033[90mINFO\033[0m] RESTARTING SERVICES ............................. " | tee -a /tmp/upgrade.log
sudo systemctl start apache2 >> /tmp/upgrade.log 2>&1
sudo systemctl restart redis-server >> /tmp/upgrade.log 2>&1
sudo systemctl restart celery >> /tmp/upgrade.log 2>&1
sudo systemctl restart cron >> /tmp/upgrade.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/upgrade.log

# cleaning /tmp
echo -n -e "[\033[90mINFO\033[0m] CLEANING /TMP DIR ............................... " | tee -a /tmp/upgrade.log
rm -fR /tmp/deephunter* /tmp/settings.py >> /tmp/upgrade.log 2>&1
echo -e "[\033[32mdone\033[0m]" | tee -a /tmp/upgrade.log

# Search for debug = true in the codebase
echo "Search for debug = true in the codebase" >> /tmp/upgrade.log
matches=$(find "$APP_PATH" -type f -name '*.py' -exec grep -EniI 'debug[[:space:]]*=[[:space:]]*true' {} + 2>/dev/null)
# Check if matches were found
if [[ -n "$matches" ]]; then
	echo ""
	echo "****************************************************************************************" | tee -a /tmp/upgrade.log
    echo "WARNING: Found 'debug = true' in the following files:" | tee -a /tmp/upgrade.log
    echo ""
    printf "%-50s %-6s %s\n" "FILE" "LINE" "MATCH" | tee -a /tmp/upgrade.log
    printf "%-50s %-6s %s\n" "----" "----" "-----" | tee -a /tmp/upgrade.log
    while IFS= read -r line; do
        file=$(echo "$line" | cut -d: -f1)
        lineno=$(echo "$line" | cut -d: -f2)
        content=$(echo "$line" | cut -d: -f3-)
        printf "%-50s %-6s %s\n" "$file" "$lineno" "$content" | tee -a /tmp/upgrade.log
    done <<< "$matches"
	echo "****************************************************************************************" | tee -a /tmp/upgrade.log
	echo ""
fi

echo ""
echo "****************************************************************************************"
echo "* Your DATA_TEMP folder has not been removed and keeps a copy of your old installation *"
echo "* If the update went well, you should manually remove any content in this directory.   *"
echo "* You may also want to remove the /tmp/upgrade.log file.                               *"
echo "****************************************************************************************"
echo ""

echo -e "[\033[90mINFO\033[0m] UPGRADE COMPLETE" | tee -a /tmp/upgrade.log
