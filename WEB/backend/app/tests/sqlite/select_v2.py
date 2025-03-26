import sys
import json
import time
import sqlite3


def run_select_test(limit=100):
    # Połączenie z bazą SQLite
    conn = sqlite3.connect(
        "/Users/mptb/Documents/Studia/Data_Science/1_sem/ZTBD/ZTBD/DB/SQLite/olist.sqlite"
    )
    conn.row_factory = sqlite3.Row  # Użycie Row jako fabryki rzędów
    cursor = conn.cursor()

    # Start pomiaru czasu
    start_time = time.time()

    # Zapytanie grupujące zamówienia według dnia
    query = """
    SELECT DATE(order_purchase_timestamp) AS day, COUNT(*) AS order_count
    FROM orders
    GROUP BY day
    ORDER BY day
    LIMIT ?
    """

    cursor.execute(query, (limit,))
    results = cursor.fetchall()

    # Przekształcenie wyników do listy słowników
    results_list = [dict(row) for row in results]

    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Zamknięcie połączenia
    cursor.close()
    conn.close()

    # Zwracanie wyniku
    result = {"time": elapsed_time, "count": len(results_list)}
    print(json.dumps(result))

    return elapsed_time


if __name__ == "__main__":
    # Pobranie limitu z argumentów
    limit = 100  # domyślnie
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    run_select_test(limit)
