import json
import os
import sqlite3
import time


def run_join_test():
    base_dir = os.path.dirname(__file__)
    project_dir = os.path.abspath(os.path.join(base_dir, "../../../../../"))
    db_path = os.path.join(project_dir, "DB", "SQLite", "olist.sqlite")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    start_time = time.time()

    # Zapytanie: dla klientów, którzy mają co najmniej 2 zatwierdzone zamówienia
    # pobieramy: id klienta, miasto, liczbę zatwierdzonych zamówień
    # oraz datę ostatniego zatwierdzonego zamówienia
    query = """
        SELECT c.customer_id, c.customer_city, agg.last_order_purchase_timestamp
        FROM customers c
        JOIN (
            SELECT customer_id,
                   COUNT(*) AS total_orders,
                   MAX(order_purchase_timestamp) AS last_order_purchase_timestamp
            FROM orders
            WHERE order_status = 'approved'
            GROUP BY customer_id
            HAVING COUNT(*) >= 1
        ) agg ON c.customer_id = agg.customer_id
        ORDER BY agg.last_order_purchase_timestamp DESC
    """
    cursor.execute(query)
    results = cursor.fetchall()
    row_count = len(results)

    end_time = time.time()
    elapsed_time = end_time - start_time

    conn.close()

    result = {"time": elapsed_time, "rows": row_count}
    print(json.dumps(result))

    return elapsed_time, results


if __name__ == "__main__":
    run_join_test()
