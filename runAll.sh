#!/bin/bash

echo "Kopiowanie olist.sqlite do DB/Postgres/import..."
cp olist.sqlite DB/Postgres/import/olist.sqlite
cp olist.sqlite DB/SQLite/olist.sqlite

echo "Uruchamianie CouchDB..."
(cd DB/CouchDB && docker-compose up -d)

echo "Uruchamianie MongoDB..."
(cd DB/MongoDB && docker-compose up -d)

echo "Uruchamianie PostgreSQL..."
(cd DB/Postgres && docker-compose up -d)

echo "Uruchamianie SQLite..."
(cd DB/SQLite && docker-compose up -d)

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "Instalacja zależności backendu..."
(cd WEB/backend && pip install -r requirements.txt)

echo "Uruchamianie migracji dla CouchDB..."
(cd DB/CouchDB &&  pip install -r requirements.txt && python3 import_all.py)

echo "Uruchamianie migracji dla MongoDB..."
(cd DB/MongoDB && pip install -r requirements.txt && python3 migrate.py)
