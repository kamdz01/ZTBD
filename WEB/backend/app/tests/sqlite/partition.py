import sqlite3
import time
import json


def setup_sqlite_partitioning():
    conn = sqlite3.connect("ecommerce.db")
    cursor = conn.cursor()

    # 1. Utworzenie zwykłej tabeli
    cursor.execute("DROP TABLE IF EXISTS orders_no_partition")
    cursor.execute(
        """
        CREATE TABLE orders_no_partition AS 
        SELECT * FROM orders
    """
    )

    # 2. Utworzenie tabel do symulacji partycjonowania
    cursor.execute("DROP TABLE IF EXISTS orders_2016")
    cursor.execute("DROP TABLE IF EXISTS orders_2017")
    cursor.execute("DROP TABLE IF EXISTS orders_2018")
    cursor.execute("DROP VIEW IF EXISTS orders_partitioned")

    cursor.execute(
        """
        CREATE TABLE orders_2016 AS 
        SELECT * FROM orders 
        WHERE order_purchase_timestamp >= '2016-01-01' AND order_purchase_timestamp < '2017-01-01'
    """
    )
    cursor.execute(
        """
        CREATE TABLE orders_2017 AS 
        SELECT * FROM orders 
        WHERE order_purchase_timestamp >= '2017-01-01' AND order_purchase_timestamp < '2018-01-01'
    """
    )
    cursor.execute(
        """
        CREATE TABLE orders_2018 AS 
        SELECT * FROM orders 
        WHERE order_purchase_timestamp >= '2018-01-01' AND order_purchase_timestamp < '2019-01-01'
    """
    )

    # 3. Utworzenie widoku łączącego wszystkie "partycje"
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

    # 4. Dodanie indeksów
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

    conn.commit()
    conn.close()

    return "Symulowane partycje w SQLite zostały skonfigurowane"


def test_sqlite_partitioning():
    results = {"partition_test": {"with_partition": {}, "without_partition": {}}}
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

    return results
