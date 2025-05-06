import psycopg2
import time
import json


def setup_postgres_partitioning():
    # Połączenie z bazą
    conn = psycopg2.connect(
        host="localhost", port=5432, database="mydb", user="admin", password="admin"
    )
    cursor = conn.cursor()

    # 1. Utworzenie zwykłych tabel dla porównania
    cursor.execute("DROP TABLE IF EXISTS orders_no_partition")
    cursor.execute(
        """
        CREATE TABLE orders_no_partition AS 
        SELECT * FROM orders
    """
    )

    # 2. Utworzenie partycjonowanej tabeli
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

    # 3. Tworzenie partycji
    cursor.execute(
        """
        CREATE TABLE orders_2016 PARTITION OF orders_partitioned
        FOR VALUES FROM ('2016-01-01') TO ('2017-01-01')
    """
    )
    cursor.execute(
        """
        CREATE TABLE orders_2017 PARTITION OF orders_partitioned
        FOR VALUES FROM ('2017-01-01') TO ('2018-01-01')
    """
    )
    cursor.execute(
        """
        CREATE TABLE orders_2018 PARTITION OF orders_partitioned
        FOR VALUES FROM ('2018-01-01') TO ('2019-01-01')
    """
    )

    # 4. Załadowanie danych do partycjonowanej tabeli
    cursor.execute(
        """
        INSERT INTO orders_partitioned 
        SELECT * FROM orders
    """
    )

    # 5. Dodanie indeksów
    cursor.execute("CREATE INDEX ON orders_no_partition (order_purchase_timestamp)")
    cursor.execute("CREATE INDEX ON orders_partitioned (order_purchase_timestamp)")

    conn.commit()
    cursor.close()
    conn.close()

    return "Partycje w PostgreSQL zostały skonfigurowane"


def test_postgres_partitioning():
    results = {"partition_test": {"with_partition": {}, "without_partition": {}}}
    conn = psycopg2.connect(
        host="localhost", port=5432, database="mydb", user="admin", password="admin"
    )
    cursor = conn.cursor()

    # Test 1: Wyszukiwanie z określonego okresu
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

    cursor.close()
    conn.close()

    return results
