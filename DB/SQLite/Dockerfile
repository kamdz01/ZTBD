FROM alpine:latest

# Instalacja SQLite
RUN apk add --no-cache sqlite

# Instalacja narzędzi do Python
RUN apk add --no-cache python3 py3-pip

# Utworzenie środowiska wirtualnego i instalacja sqlite-web
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"
RUN pip install sqlite-web

# Utworzenie katalogu na dane
WORKDIR /data

# Domyślna komenda - uruchamia interfejs sqlite-web
CMD ["sqlite_web", "--host", "0.0.0.0", "/data/olist.sqlite"]