# ZTBD

Database engines comparison project

# DOCKER

### CouchDB

```zsh
docker-compose up
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 import_all.py
```

### MongoDB

```zsh
docker-compose up
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 migrate.py
```

### PostgreSql

```zsh
cp olist.sqlite DB/Postgres/import/olist.sqlite
docker-compose up
```

### SQLite

```zsh
docker-compose up
```

- Dockerfile
- docker-compose.yml

# BACKEND

```zsh
python3 -m venv .venv
source .venv/bin/activate
```

```zsh
pip install -r requirements.txt
uvicorn app.main:app --reload
```

# FRONTEND

```zsh
npm i
npm run dev
```
