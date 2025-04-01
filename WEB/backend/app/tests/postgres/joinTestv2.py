import sys
import json
import time
import psycopg2
import psycopg2.extras


def run_join_test(limit=10):
    """
    Wykonuje złożone zapytanie z wieloma JOIN-ami i zwraca w JSON
    czas wykonania zapytania.
    """
    # Połączenie z PostgreSQL
    conn = psycopg2.connect(
        host="localhost", port=5432, database="mydb", user="admin", password="admin"
    )

    cursor = conn.cursor()

    # Rozpoczęcie pomiaru czasu
    start_time = time.time()

    query = """
        SELECT
            o.order_id,
            c.customer_city,
            c.customer_state,
            s.seller_city,
            s.seller_state,
            p.product_category_name,
            pct.product_category_name_english,
            r.review_score
        FROM orders AS o
        JOIN customers AS c
            ON o.customer_id = c.customer_id
        JOIN order_items AS oi
            ON o.order_id = oi.order_id
        JOIN products AS p
            ON oi.product_id = p.product_id
        LEFT JOIN product_category_name_translation AS pct
            ON p.product_category_name = pct.product_category_name
        JOIN sellers AS s
            ON oi.seller_id = s.seller_id
        LEFT JOIN order_reviews AS r
            ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered'
        ORDER BY o.order_purchase_timestamp DESC
        LIMIT %s
    """

    # Wykonanie zapytania
    cursor.execute("BEGIN TRANSACTION")
    cursor.execute(query, (limit,))
    rows = cursor.fetchall()
    conn.commit()

    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Zamknięcie połączenia
    cursor.close()
    conn.close()

    # Zwrócenie wyniku w formacie JSON
    result = {"time": elapsed_time}
    print(json.dumps(result))

    return elapsed_time


if __name__ == "__main__":
    # Domyślnie pobieramy 10 rekordów, chyba że podano inny limit w argumentach
    limit = 10
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    run_join_test(limit)