#!/bin/bash
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "Instalacja zależności backendu..."
(cd WEB/backend && pip install -r requirements.txt)

echo "Uruchamianie migracji dla CouchDB..."
(cd DB/CouchDB &&  pip install -r requirements.txt && python3 import_all.py)

# echo "Uruchamianie migracji dla MongoDB..."
# (cd DB/MongoDB && pip install -r requirements.txt && python3 migrate.py)
