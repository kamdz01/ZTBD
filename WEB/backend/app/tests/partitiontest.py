import json
import time
import matplotlib.pyplot as plt
import numpy as np
import datetime
import psycopg2


def log_message(db_type, message):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{db_type}] {message}")


def setup_postgres_partitioning():
    """
    Konfiguruje partycjonowanie dla PostgreSQL.
    Tworzy tabele bez partycjonowania i z partycjonowaniem dla porównania.
    """
    log_message("PostgreSQL", "Rozpoczynam konfigurację partycjonowania...")
    try:
        # Połączenie z bazą
        log_message("PostgreSQL", "Łączenie z bazą danych...")
        conn = psycopg2.connect(
            host="localhost", port=5432, database="mydb", user="admin", password="admin"
        )
        cursor = conn.cursor()

        # 1. Utworzenie zwykłej tabeli dla porównania
        try:
            log_message("PostgreSQL", "Tworzenie tabeli bez partycjonowania...")
            cursor.execute("DROP TABLE IF EXISTS orders_no_partition")
            cursor.execute(
                """
                CREATE TABLE orders_no_partition AS 
                SELECT * FROM orders
            """
            )
            log_message("PostgreSQL", "Tabela bez partycjonowania została utworzona")
        except Exception as e:
            log_message("PostgreSQL", f"BŁĄD podczas tworzenia tabeli zwykłej: {e}")

        # 2. Utworzenie partycjonowanej tabeli
        try:
            log_message("PostgreSQL", "Tworzenie tabeli z partycjonowaniem...")
            cursor.execute("DROP TABLE IF EXISTS orders_partitioned CASCADE")
            cursor.execute(
                """
                CREATE TABLE orders_partitioned (
                    id SERIAL,
                    order_id VARCHAR(50),
                    customer_id VARCHAR(50),
                    order_status VARCHAR(20),
                    order_purchase_timestamp TIMESTAMP,
                    order_approved_at TIMESTAMP,
                    order_delivered_carrier_date TIMESTAMP,
                    order_delivered_customer_date TIMESTAMP,
                    order_estimated_delivery_date TIMESTAMP
                ) PARTITION BY RANGE (order_purchase_timestamp)
            """
            )
            log_message(
                "PostgreSQL", "Struktura tabeli partycjonowanej została utworzona"
            )

            # 3. Tworzenie partycji
            log_message("PostgreSQL", "Tworzenie partycji dla lat 2016-2018...")
            cursor.execute(
                """
                CREATE TABLE orders_2016 PARTITION OF orders_partitioned
                FOR VALUES FROM ('2016-01-01') TO ('2017-01-01')
            """
            )
            log_message("PostgreSQL", "Utworzono partycję 2016")

            cursor.execute(
                """
                CREATE TABLE orders_2017 PARTITION OF orders_partitioned
                FOR VALUES FROM ('2017-01-01') TO ('2018-01-01')
            """
            )
            log_message("PostgreSQL", "Utworzono partycję 2017")

            cursor.execute(
                """
                CREATE TABLE orders_2018 PARTITION OF orders_partitioned
                FOR VALUES FROM ('2018-01-01') TO ('2019-01-01')
            """
            )
            log_message("PostgreSQL", "Utworzono partycję 2018")

            # 4. Załadowanie danych do partycjonowanej tabeli
            log_message("PostgreSQL", "Ładowanie danych do partycjonowanej tabeli...")
            cursor.execute(
                """
                INSERT INTO orders_partitioned (
                    order_id, customer_id, order_status, 
                    order_purchase_timestamp, order_approved_at,
                    order_delivered_carrier_date, order_delivered_customer_date,
                    order_estimated_delivery_date
                )
                SELECT 
                    order_id, customer_id, order_status,
                    order_purchase_timestamp::timestamp, order_approved_at::timestamp,
                    order_delivered_carrier_date::timestamp, order_delivered_customer_date::timestamp,
                    order_estimated_delivery_date::timestamp
                FROM orders
            """
            )
            log_message(
                "PostgreSQL", "Dane zostały załadowane do tabeli partycjonowanej"
            )
        except Exception as e:
            log_message(
                "PostgreSQL", f"BŁĄD podczas tworzenia tabeli partycjonowanej: {e}"
            )

        # 5. Dodanie indeksów
        try:
            log_message("PostgreSQL", "Tworzenie indeksów...")
            cursor.execute(
                "CREATE INDEX ON orders_no_partition (order_purchase_timestamp)"
            )
            cursor.execute(
                "CREATE INDEX ON orders_partitioned (order_purchase_timestamp)"
            )
            log_message("PostgreSQL", "Indeksy zostały utworzone")
        except Exception as e:
            log_message("PostgreSQL", f"BŁĄD podczas tworzenia indeksów: {e}")

        conn.commit()
        cursor.close()
        conn.close()
        log_message("PostgreSQL", "Konfiguracja partycjonowania zakończona pomyślnie")

        return "Partycje w PostgreSQL zostały skonfigurowane"
    except Exception as e:
        log_message("PostgreSQL", f"KRYTYCZNY BŁĄD konfiguracji: {e}")
        return f"Błąd konfiguracji partycji w PostgreSQL: {e}"


def test_postgres_partitioning():
    """
    Testuje wydajność partycjonowania w PostgreSQL poprzez porównanie czasów
    wykonania zapytań na tabelach partycjonowanych i zwykłych.
    """
    log_message("PostgreSQL", "Rozpoczynam test wydajności partycjonowania...")
    results = {"partition_test": {"with_partition": {}, "without_partition": {}}}
    try:
        conn = psycopg2.connect(
            host="localhost", port=5432, database="mydb", user="admin", password="admin"
        )
        cursor = conn.cursor()

        # Test 1: Wyszukiwanie z określonego okresu
        log_message("PostgreSQL", "Test 1: Zapytanie do tabeli bez partycjonowania...")
        start_time = time.time()
        cursor.execute(
            """
            SELECT COUNT(*) FROM orders_no_partition 
            WHERE order_purchase_timestamp BETWEEN '2017-01-01' AND '2017-06-30'
        """
        )
        count = cursor.fetchone()[0]
        no_partition_time = time.time() - start_time
        results["partition_test"]["without_partition"]["time"] = no_partition_time
        results["partition_test"]["without_partition"]["rows"] = count
        log_message(
            "PostgreSQL",
            f"Znaleziono {count} wierszy w czasie {no_partition_time:.4f}s",
        )

        log_message("PostgreSQL", "Test 1: Zapytanie do tabeli z partycjonowaniem...")
        start_time = time.time()
        cursor.execute(
            """
            SELECT COUNT(*) FROM orders_partitioned 
            WHERE order_purchase_timestamp BETWEEN '2017-01-01' AND '2017-06-30'
        """
        )
        count = cursor.fetchone()[0]
        partition_time = time.time() - start_time
        results["partition_test"]["with_partition"]["time"] = partition_time
        results["partition_test"]["with_partition"]["rows"] = count
        log_message(
            "PostgreSQL", f"Znaleziono {count} wierszy w czasie {partition_time:.4f}s"
        )

        # Obliczenie procentowej różnicy w wydajności
        if no_partition_time > 0:
            improvement = (
                (no_partition_time - partition_time) / no_partition_time
            ) * 100
            log_message("PostgreSQL", f"Poprawa wydajności: {improvement:.2f}%")

        cursor.close()
        conn.close()
        log_message("PostgreSQL", "Test zakończony pomyślnie")
    except Exception as e:
        log_message("PostgreSQL", f"BŁĄD podczas testowania: {e}")
        results["partition_test"]["error"] = str(e)

    return results


# MongoDB partitioning
from pymongo import MongoClient


def setup_mongodb_partitioning():
    """
    Konfiguruje partycjonowanie dla MongoDB.
    Tworzy kolekcje bez partycjonowania i z partycjonowaniem dla porównania.
    """
    try:
        log_message("MONGO", "Łączenie z bazą danych...")
        client = MongoClient("mongodb://admin:admin@localhost:27017/")
        db = client["ecommerce"]

        # 1. Utworzenie kolekcji bez partycjonowania
        if "orders_no_partition" in db.list_collection_names():
            db.orders_no_partition.drop()
        db.orders.aggregate([{"$match": {}}, {"$out": "orders_no_partition"}])

        # 2. Utworzenie kolekcji z partycjonowaniem czasowym
        if "orders_partitioned_2016" in db.list_collection_names():
            db.orders_partitioned_2016.drop()
        if "orders_partitioned_2017" in db.list_collection_names():
            db.orders_partitioned_2017.drop()
        if "orders_partitioned_2018" in db.list_collection_names():
            db.orders_partitioned_2018.drop()

        # Podział danych według lat
        db.orders.aggregate(
            [
                {
                    "$match": {
                        "order_purchase_timestamp": {
                            "$gte": "2016-01-01",
                            "$lt": "2017-01-01",
                        }
                    }
                },
                {"$out": "orders_partitioned_2016"},
            ]
        )
        db.orders.aggregate(
            [
                {
                    "$match": {
                        "order_purchase_timestamp": {
                            "$gte": "2017-01-01",
                            "$lt": "2018-01-01",
                        }
                    }
                },
                {"$out": "orders_partitioned_2017"},
            ]
        )
        db.orders.aggregate(
            [
                {
                    "$match": {
                        "order_purchase_timestamp": {
                            "$gte": "2018-01-01",
                            "$lt": "2019-01-01",
                        }
                    }
                },
                {"$out": "orders_partitioned_2018"},
            ]
        )

        # 3. Utworzenie indeksów
        log_message("MONGO", "Indeksy...")
        db.orders_no_partition.create_index("order_purchase_timestamp")
        db.orders_partitioned_2016.create_index("order_purchase_timestamp")
        db.orders_partitioned_2017.create_index("order_purchase_timestamp")
        db.orders_partitioned_2018.create_index("order_purchase_timestamp")

        return "Partycje w MongoDB zostały skonfigurowane"
    except Exception as e:
        return f"Błąd konfiguracji partycji w MongoDB: {e}"


def test_mongodb_partitioning():
    """
    Testuje wydajność partycjonowania w MongoDB poprzez porównanie czasów
    wykonania zapytań na kolekcjach partycjonowanych i zwykłych.
    """
    results = {"partition_test": {"with_partition": {}, "without_partition": {}}}
    log_message("MONGO", "test_mongodb_partitioning")

    try:
        client = MongoClient("mongodb://admin:admin@localhost:27017/")
        db = client["ecommerce"]

        # Test bez partycjonowania
        start_time = time.time()
        count = db.orders_no_partition.count_documents(
            {"order_purchase_timestamp": {"$gte": "2017-01-01", "$lte": "2017-06-30"}}
        )
        no_partition_time = time.time() - start_time
        results["partition_test"]["without_partition"]["time"] = no_partition_time
        results["partition_test"]["without_partition"]["rows"] = count

        # Test z partycjonowaniem (zapytanie tylko do odpowiedniej kolekcji)
        start_time = time.time()
        count = db.orders_partitioned_2017.count_documents(
            {"order_purchase_timestamp": {"$gte": "2017-01-01", "$lte": "2017-06-30"}}
        )
        partition_time = time.time() - start_time
        results["partition_test"]["with_partition"]["time"] = partition_time
        results["partition_test"]["with_partition"]["rows"] = count
    except Exception as e:
        print(f"Błąd podczas testowania partycjonowania MongoDB: {e}")
        results["partition_test"]["error"] = str(e)

    return results


# CouchDB partitioning
import requests


def setup_couchdb_partitioning():
    """
    Konfiguruje partycjonowanie dla CouchDB z ograniczoną ilością danych.
    """
    try:
        couch_url = "http://admin:admin@localhost:5984"
        log_message("COUCH", "Łączenie z bazą danych...")

        # 1. Sprawdź czy baza orders istnieje
        check_orders = requests.get(f"{couch_url}/orders")
        if check_orders.status_code != 200:
            log_message("COUCH", "BŁĄD: Baza orders nie istnieje lub brak dostępu")
            return "Błąd: Baza orders nie istnieje w CouchDB"

        # 2. Przygotuj bazy danych
        log_message("COUCH", "Usuwanie i tworzenie baz danych testowych...")
        requests.delete(f"{couch_url}/orders_no_partition")
        requests.put(f"{couch_url}/orders_no_partition")

        requests.delete(f"{couch_url}/orders_2016")
        requests.put(f"{couch_url}/orders_2016")

        requests.delete(f"{couch_url}/orders_2017")
        requests.put(f"{couch_url}/orders_2017")

        requests.delete(f"{couch_url}/orders_2018")
        requests.put(f"{couch_url}/orders_2018")

        # 3. Kopiuj ograniczoną ilość danych (max 100 dokumentów z każdego roku)
        log_message(
            "COUCH",
            "Kopiowanie danych do baz (ograniczone do 100 dokumentów z każdego roku)...",
        )

        # Wstaw do bazy bez partycjonowania
        sample_query = {"selector": {}, "limit": 250}  # Ograniczenie do 250 dokumentów

        sample_docs = (
            requests.post(f"{couch_url}/orders/_find", json=sample_query)
            .json()
            .get("docs", [])
        )
        log_message("COUCH", f"Pobrano {len(sample_docs)} przykładowych dokumentów")

        bulk_docs = {"docs": []}
        for doc in sample_docs:
            if "_id" in doc:
                doc_copy = doc.copy()
                if "_rev" in doc_copy:
                    del doc_copy["_rev"]  # Usuń _rev przy kopiowaniu
                bulk_docs["docs"].append(doc_copy)

        # Wstaw dane zbiorczo
        if bulk_docs["docs"]:
            bulk_response = requests.post(
                f"{couch_url}/orders_no_partition/_bulk_docs", json=bulk_docs
            )
            log_message(
                "COUCH",
                f"Wstawiono dokumenty do bazy orders_no_partition, status: {bulk_response.status_code}",
            )

        # Kopiowanie danych do odpowiednich baz według roku
        years = ["2016", "2017", "2018"]

        for year in years:
            year_query = {
                "selector": {
                    "order_purchase_timestamp": {
                        "$gte": f"{year}-01-01",
                        "$lt": f"{int(year)+1}-01-01",
                    }
                },
                "limit": 100,  # Ograniczenie do 100 dokumentów na rok
            }

            year_docs = (
                requests.post(f"{couch_url}/orders/_find", json=year_query)
                .json()
                .get("docs", [])
            )
            log_message("COUCH", f"Pobrano {len(year_docs)} dokumentów z roku {year}")

            bulk_year_docs = {"docs": []}
            for doc in year_docs:
                if "_id" in doc:
                    doc_copy = doc.copy()
                    if "_rev" in doc_copy:
                        del doc_copy["_rev"]
                    bulk_year_docs["docs"].append(doc_copy)

            if bulk_year_docs["docs"]:
                bulk_response = requests.post(
                    f"{couch_url}/orders_{year}/_bulk_docs", json=bulk_year_docs
                )
                log_message(
                    "COUCH",
                    f"Wstawiono dokumenty do bazy orders_{year}, status: {bulk_response.status_code}",
                )

        # 4. Dodanie indeksów
        log_message("COUCH", "Tworzenie indeksów...")
        for db in ["orders_no_partition", "orders_2016", "orders_2017", "orders_2018"]:
            index_response = requests.post(
                f"{couch_url}/{db}/_index",
                json={
                    "index": {"fields": ["order_purchase_timestamp"]},
                    "name": "timestamp_idx",
                },
            )
            log_message(
                "COUCH",
                f"Utworzono indeks dla {db}, status: {index_response.status_code}",
            )

        log_message("COUCH", "Konfiguracja CouchDB zakończona pomyślnie")
        return "Partycje w CouchDB zostały skonfigurowane (ograniczony zbiór danych)"
    except Exception as e:
        log_message("COUCH", f"KRYTYCZNY BŁĄD: {e}")
        return f"Błąd konfiguracji partycji w CouchDB: {e}"


def test_couchdb_partitioning():
    """
    Testuje wydajność partycjonowania w CouchDB poprzez porównanie czasów
    wykonania zapytań na bazach partycjonowanych i zwykłych.
    """
    results = {"partition_test": {"with_partition": {}, "without_partition": {}}}
    couch_url = "http://admin:admin@localhost:5984"

    try:
        # Test bez partycjonowania
        start_time = time.time()
        query = {
            "selector": {
                "order_purchase_timestamp": {"$gte": "2017-01-01", "$lte": "2017-06-30"}
            }
        }
        response = requests.post(f"{couch_url}/orders_no_partition/_find", json=query)

        if response.status_code == 200:
            docs = response.json().get("docs", [])
            no_partition_time = time.time() - start_time
            results["partition_test"]["without_partition"]["time"] = no_partition_time
            results["partition_test"]["without_partition"]["rows"] = len(docs)
        else:
            print(f"Błąd w zapytaniu do zwykłej bazy CouchDB: {response.status_code}")
            results["partition_test"]["without_partition"]["error"] = response.text

        # Test z partycjonowaniem - sprawdzamy obie możliwe konfiguracje
        start_time = time.time()

        try:
            # Próba użycia natywnych partycji CouchDB 3.0+
            response = requests.post(
                f"{couch_url}/orders_partitioned/_partition/2017/_find",
                json={
                    "selector": {
                        "order_purchase_timestamp": {
                            "$gte": "2017-01-01",
                            "$lte": "2017-06-30",
                        }
                    }
                },
            )

            if response.status_code == 200:
                docs = response.json().get("docs", [])
                partition_time = time.time() - start_time
                results["partition_test"]["with_partition"]["time"] = partition_time
                results["partition_test"]["with_partition"]["rows"] = len(docs)
            else:
                # Alternatywnie sprawdzamy bazę z określonego roku
                response = requests.post(
                    f"{couch_url}/orders_2017/_find",
                    json={
                        "selector": {
                            "order_purchase_timestamp": {
                                "$gte": "2017-01-01",
                                "$lte": "2017-06-30",
                            }
                        }
                    },
                )

                if response.status_code == 200:
                    docs = response.json().get("docs", [])
                    partition_time = time.time() - start_time
                    results["partition_test"]["with_partition"]["time"] = partition_time
                    results["partition_test"]["with_partition"]["rows"] = len(docs)
                else:
                    print(
                        f"Błąd w zapytaniu do alternatywnej bazy CouchDB: {response.status_code}"
                    )
                    results["partition_test"]["with_partition"]["error"] = response.text
        except Exception as e:
            print(f"Błąd podczas testowania partycji CouchDB: {e}")
            results["partition_test"]["with_partition"]["error"] = str(e)
    except Exception as e:
        print(f"Błąd ogólny podczas testowania CouchDB: {e}")
        results["partition_test"]["error"] = str(e)

    return results


# SQLite partitioning
import sqlite3


def setup_sqlite_partitioning():
    """
    Konfiguruje partycjonowanie dla SQLite.
    Tworzy tabele bez partycjonowania i z symulowanym partycjonowaniem dla porównania.
    """
    try:
        log_message("SQLITE", "Łączenie z bazą danych...")
        conn = sqlite3.connect("ecommerce.db")
        cursor = conn.cursor()

        # Sprawdź czy tabela orders istnieje
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='orders'"
        )
        if not cursor.fetchone():
            log_message(
                "SQLITE", "BŁĄD: Brak tabeli orders! Tworzę przykładową tabelę..."
            )
            # Jeśli tabela orders nie istnieje, utwórz przykładową
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    customer_id TEXT,
                    order_status TEXT,
                    order_purchase_timestamp TEXT,
                    order_approved_at TEXT,
                    order_delivered_carrier_date TEXT,
                    order_delivered_customer_date TEXT,
                    order_estimated_delivery_date TEXT
                )
            """
            )
            # Dodaj przykładowe dane
            cursor.execute(
                """
                INSERT INTO orders (order_id, customer_id, order_status, order_purchase_timestamp)
                VALUES 
                ('test1', 'cust1', 'delivered', '2016-05-01'),
                ('test2', 'cust2', 'delivered', '2017-02-15'),
                ('test3', 'cust3', 'canceled', '2017-04-10'),
                ('test4', 'cust4', 'delivered', '2018-01-20')
            """
            )
            conn.commit()
            log_message("SQLITE", "Utworzono przykładową tabelę orders")

        # 1. Usuwamy istniejące tabele jeśli istnieją
        log_message("SQLITE", "Usuwanie starych tabel...")
        cursor.execute("DROP TABLE IF EXISTS orders_no_partition")
        cursor.execute("DROP TABLE IF EXISTS orders_2016")
        cursor.execute("DROP TABLE IF EXISTS orders_2017")
        cursor.execute("DROP TABLE IF EXISTS orders_2018")
        cursor.execute("DROP VIEW IF EXISTS orders_partitioned")

        # 2. Utworzenie zwykłej tabeli
        log_message("SQLITE", "Tworzenie tabeli bez partycjonowania...")
        cursor.execute(
            """
            CREATE TABLE orders_no_partition AS 
            SELECT * FROM orders
        """
        )
        log_message("SQLITE", f"Utworzono tabelę - sprawdzam liczbę wierszy:")
        cursor.execute("SELECT COUNT(*) FROM orders_no_partition")
        count = cursor.fetchone()[0]
        log_message("SQLITE", f"orders_no_partition zawiera {count} wierszy")

        # 3. Utworzenie tabel do symulacji partycjonowania
        log_message("SQLITE", "Tworzenie tabel symulujących partycje...")
        cursor.execute(
            """
            CREATE TABLE orders_2016 AS 
            SELECT * FROM orders 
            WHERE order_purchase_timestamp >= '2016-01-01' AND order_purchase_timestamp < '2017-01-01'
        """
        )
        cursor.execute("SELECT COUNT(*) FROM orders_2016")
        count = cursor.fetchone()[0]
        log_message("SQLITE", f"Partycja 2016: {count} wierszy")

        cursor.execute(
            """
            CREATE TABLE orders_2017 AS 
            SELECT * FROM orders 
            WHERE order_purchase_timestamp >= '2017-01-01' AND order_purchase_timestamp < '2018-01-01'
        """
        )
        cursor.execute("SELECT COUNT(*) FROM orders_2017")
        count = cursor.fetchone()[0]
        log_message("SQLITE", f"Partycja 2017: {count} wierszy")

        cursor.execute(
            """
            CREATE TABLE orders_2018 AS 
            SELECT * FROM orders 
            WHERE order_purchase_timestamp >= '2018-01-01' AND order_purchase_timestamp < '2019-01-01'
        """
        )
        cursor.execute("SELECT COUNT(*) FROM orders_2018")
        count = cursor.fetchone()[0]
        log_message("SQLITE", f"Partycja 2018: {count} wierszy")

        # 4. Utworzenie widoku łączącego wszystkie "partycje"
        log_message("SQLITE", "Tworzenie widoku łączącego partycje...")
        cursor.execute(
            """
            CREATE VIEW orders_partitioned AS
            SELECT * FROM orders_2016
            UNION ALL
            SELECT * FROM orders_2017
            UNION ALL
            SELECT * FROM orders_2018
        """
        )

        # 5. Dodanie indeksów
        log_message("SQLITE", "Tworzenie indeksów...")
        cursor.execute(
            "CREATE INDEX idx_no_part_timestamp ON orders_no_partition(order_purchase_timestamp)"
        )
        cursor.execute(
            "CREATE INDEX idx_2016_timestamp ON orders_2016(order_purchase_timestamp)"
        )
        cursor.execute(
            "CREATE INDEX idx_2017_timestamp ON orders_2017(order_purchase_timestamp)"
        )
        cursor.execute(
            "CREATE INDEX idx_2018_timestamp ON orders_2018(order_purchase_timestamp)"
        )
        log_message("SQLITE", "Indeksy zostały utworzone")

        conn.commit()
        conn.close()
        log_message("SQLITE", "Konfiguracja zakończona pomyślnie")
        return "Symulowane partycje w SQLite zostały skonfigurowane"
    except Exception as e:
        log_message("SQLITE", f"KRYTYCZNY BŁĄD: {e}")
        return f"Błąd konfiguracji symulowanych partycji w SQLite: {e}"


def test_sqlite_partitioning():
    """
    Testuje wydajność symulowanego partycjonowania w SQLite poprzez porównanie czasów
    wykonania zapytań na tabelach partycjonowanych i zwykłych.
    """
    results = {"partition_test": {"with_partition": {}, "without_partition": {}}}
    try:
        conn = sqlite3.connect("ecommerce.db")
        cursor = conn.cursor()

        # Test bez partycjonowania
        start_time = time.time()
        cursor.execute(
            """
            SELECT COUNT(*) FROM orders_no_partition
            WHERE order_purchase_timestamp BETWEEN '2017-01-01' AND '2017-06-30'
        """
        )
        count = cursor.fetchone()[0]
        no_partition_time = time.time() - start_time
        results["partition_test"]["without_partition"]["time"] = no_partition_time
        results["partition_test"]["without_partition"]["rows"] = count

        # Test z partycjonowaniem (zapytanie bezpośrednio do partycji 2017)
        start_time = time.time()
        cursor.execute(
            """
            SELECT COUNT(*) FROM orders_2017
            WHERE order_purchase_timestamp BETWEEN '2017-01-01' AND '2017-06-30'
        """
        )
        count = cursor.fetchone()[0]
        partition_time = time.time() - start_time
        results["partition_test"]["with_partition"]["time"] = partition_time
        results["partition_test"]["with_partition"]["rows"] = count

        conn.close()
    except Exception as e:
        print(f"Błąd podczas testowania partycjonowania SQLite: {e}")
        results["partition_test"]["error"] = str(e)

    return results


# Funkcje do uruchamiania wszystkich testów i generowania wykresu
def run_all_partition_tests():
    """
    Uruchamia testy partycjonowania dla wszystkich baz danych.
    """
    # Konfiguracja partycjonowania dla wszystkich baz
    log_message("CHART", "Rozpoczynam generowanie wykresu...")
    setup_results = {
        "postgres": setup_postgres_partitioning(),
        "mongodb": setup_mongodb_partitioning(),
        "couchdb": setup_couchdb_partitioning(),
        "sqlite": setup_sqlite_partitioning(),
    }
    print("Konfiguracja partycjonowania zakończona:")
    print(json.dumps(setup_results, indent=2))

    # Uruchomienie testów
    test_results = {
        "postgres": test_postgres_partitioning(),
        "mongodb": test_mongodb_partitioning(),
        "couchdb": test_couchdb_partitioning(),
        "sqlite": test_sqlite_partitioning(),
    }

    # Obliczenie poprawy wydajności
    for db_name, results in test_results.items():
        if "partition_test" in results:
            if (
                "without_partition" in results["partition_test"]
                and "with_partition" in results["partition_test"]
            ):
                if (
                    "time" in results["partition_test"]["without_partition"]
                    and "time" in results["partition_test"]["with_partition"]
                ):
                    non_partition_time = results["partition_test"]["without_partition"][
                        "time"
                    ]
                    partition_time = results["partition_test"]["with_partition"]["time"]
                    if non_partition_time > 0:
                        improvement = (
                            (non_partition_time - partition_time) / non_partition_time
                        ) * 100
                        test_results[db_name]["partition_test"][
                            "improvement"
                        ] = f"{improvement:.2f}%"
                    else:
                        test_results[db_name]["partition_test"]["improvement"] = "0.00%"

    # Zapisanie wyników
    with open("partition_test_results.json", "w") as f:
        json.dump(test_results, f, indent=2)

    # Wygenerowanie wykresu porównawczego
    generate_comparison_chart(test_results)

    return test_results


def generate_comparison_chart(results):
    """
    Generuje ulepszony wykres porównawczy czasów wykonania zapytań dla różnych baz danych.
    """
    log_message("CHART", "Rozpoczynam generowanie ulepszonego wykresu...")
    db_names = list(results.keys())
    no_partition_times = []
    partition_times = []
    improvements = []

    for db in db_names:
        if "partition_test" in results[db]:
            if (
                "without_partition" in results[db]["partition_test"]
                and "time" in results[db]["partition_test"]["without_partition"]
            ):
                no_partition_times.append(
                    results[db]["partition_test"]["without_partition"]["time"]
                )
            else:
                no_partition_times.append(0)

            if (
                "with_partition" in results[db]["partition_test"]
                and "time" in results[db]["partition_test"]["with_partition"]
            ):
                partition_times.append(
                    results[db]["partition_test"]["with_partition"]["time"]
                )
            else:
                partition_times.append(0)

            if "improvement" in results[db]["partition_test"]:
                imp_str = results[db]["partition_test"]["improvement"]
                improvements.append(float(imp_str.rstrip("%")))
            else:
                improvements.append(0)

    # Stwórz figurę z dwoma podwykresami
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(14, 12), gridspec_kw={"height_ratios": [2, 1]}
    )

    # PODWYKRES 1: Czasy wykonania - skala logarytmiczna
    x = np.arange(len(db_names))
    width = 0.35

    # Dodaj minimalne wartości dla skali logarytmicznej
    no_partition_times_log = [max(t, 1e-6) for t in no_partition_times]
    partition_times_log = [max(t, 1e-6) for t in partition_times]

    rects1 = ax1.bar(
        x - width / 2,
        no_partition_times_log,
        width,
        label="Bez partycjonowania",
        color="#ff7f0e",
        alpha=0.8,
    )
    rects2 = ax1.bar(
        x + width / 2,
        partition_times_log,
        width,
        label="Z partycjonowaniem",
        color="#1f77b4",
        alpha=0.8,
    )

    # Ustaw skalę logarytmiczną dla lepszej wizualizacji
    ax1.set_yscale("log")
    ax1.set_ylabel("Czas wykonania [s] (skala logarytmiczna)", fontsize=12)
    ax1.set_title(
        "Porównanie wydajności partycjonowania w różnych bazach danych",
        fontsize=14,
        fontweight="bold",
    )
    ax1.set_xticks(x)
    ax1.set_xticklabels(db_names, fontsize=12)
    ax1.legend(fontsize=12)
    ax1.grid(True, alpha=0.3, which="both")

    # Dodaj etykiety wartości na słupkach
    def add_labels(rects, times):
        for i, (rect, time) in enumerate(zip(rects, times)):
            height = rect.get_height()
            # Usuń próg 0.001 aby wyświetlać wszystkie wartości
            if time > 0:  # Pokazuj wszystkie czasy > 0
                # Dostosuj format w zależności od wielkości czasu
                if time < 0.001:
                    time_str = f"{time:.8f}s"
                elif time < 0.01:
                    time_str = f"{time:.6f}s"
                else:
                    time_str = f"{time:.5f}s"

                ax1.annotate(
                    time_str,
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 punkty nad szczytem
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    rotation=0,
                )

    add_labels(rects1, no_partition_times)
    add_labels(rects2, partition_times)

    # PODWYKRES 2: Procentowa poprawa wydajności
    ax2.bar(x, improvements, color="green", alpha=0.7)
    ax2.set_ylabel("Poprawa wydajności [%]", fontsize=12)
    ax2.set_title(
        "Procentowa poprawa wydajności dzięki partycjonowaniu",
        fontsize=14,
        fontweight="bold",
    )
    ax2.set_xticks(x)
    ax2.set_xticklabels(db_names, fontsize=12)
    ax2.grid(True, alpha=0.3)

    # Dodaj tabele z dokładnymi wartościami na dole wykresu
    table_data = []
    for i, db in enumerate(db_names):
        table_data.append(
            [
                db,
                f"{no_partition_times[i]:.6f}s",
                f"{partition_times[i]:.6f}s",
                f"{improvements[i]:.2f}%",
            ]
        )

    # Dodaj tabelę pod wykresami
    ax3 = fig.add_subplot(313)
    ax3.axis("off")
    table = ax3.table(
        cellText=table_data,
        colLabels=[
            "Baza danych",
            "Bez partycjonowania",
            "Z partycjonowaniem",
            "Poprawa (%)",
        ],
        loc="center",
        cellLoc="center",
        bbox=[0, 0, 1, 1],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    plt.tight_layout(pad=3.0)
    plt.savefig("partition_comparison.png", dpi=150)
    plt.savefig("partition_comparison.pdf")  # Wersja wektorowa do dokumentów
    plt.close()
    log_message(
        "CHART",
        "Wykres zapisany jako partition_comparison.png i partition_comparison.pdf",
    )


if __name__ == "__main__":
    results = run_all_partition_tests()
    print("Wyniki testów partycjonowania:")
    print(json.dumps(results, indent=2))
