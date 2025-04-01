import sys
import json
import time
import psycopg2
import psycopg2.extras


def run_join_test():
    # Połączenie z PostgreSQL
    conn = psycopg2.connect(
        host="localhost", port=5432, database="mydb", user="admin", password="admin"
    )
    
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