#!/bin/sh
source /data/venv/bin/activate
cd /data/deephunter/
python3 manage.py loaddata install/fixtures/auth_group.json
python3 manage.py loaddata install/fixtures/qm_country.json
python3 manage.py loaddata install/fixtures/qm_threatactor.json
python3 manage.py loaddata install/fixtures/qm_threatname.json
python3 manage.py loaddata install/fixtures/qm_vulnerability.json
python3 manage.py loaddata install/fixtures/qm_mitretactic.json
python3 manage.py loaddata install/fixtures/qm_mitretechnique.json
python3 manage.py loaddata install/fixtures/qm_tag.json
python3 manage.py loaddata install/fixtures/qm_category.json
python3 manage.py loaddata install/fixtures/qm_targetos.json
python3 manage.py loaddata install/fixtures/qm_analytic.json
python3 manage.py loaddata install/fixtures/connectors.json
