import os
import sys
import json
import time
import sqlite3
from datetime import datetime


def run_join_test(limit=10):
    """
    Wykonuje złożone zapytanie z wieloma JOIN-ami i zwraca w JSON
    czas wykonania zapytania. Struktura analogiczna do fillTest.py.
    """

    # Ustalanie ścieżki do bazy (dostosuj do własnego środowiska)
    base_dir = os.path.dirname(__file__)
    project_dir = os.path.abspath(os.path.join(base_dir, "../../../../../"))
    db_path = os.path.join(project_dir, "DB", "SQLite", "olist.sqlite")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Rozpoczęcie pomiaru czasu
    start_time = time.time()

    # Przykładowe, bardziej złożone zapytanie:
    # Pobiera zamówienia z tabeli orders wraz z informacjami o kliencie,
    # sprzedawcy, produkcie i oceną recenzji. 
    # Ograniczamy wynik do rekordów ze statusem 'delivered'.
    query = f"""
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
        LIMIT ?
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