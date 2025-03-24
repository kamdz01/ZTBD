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
