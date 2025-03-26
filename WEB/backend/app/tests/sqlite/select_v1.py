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

    # Kompleksowe zapytanie z wieloma JOIN-ami
    query = """
    SELECT 
        o.order_id, 
        o.order_status,
        o.order_purchase_timestamp,
        c.customer_id,
        c.customer_city,
        c.customer_state,
        oi.order_item_id,
        oi.price,
        oi.freight_value,
        p.product_id,
        p.product_category_name,
        s.seller_id,
        s.seller_city,
        s.seller_state,
        op.payment_type,
        op.payment_value,
        or_review.review_score
    FROM 
        orders o
    JOIN 
        customers c ON o.customer_id = c.customer_id
    JOIN 
        order_items oi ON o.order_id = oi.order_id
    JOIN 
        products p ON oi.product_id = p.product_id
    JOIN 
        sellers s ON oi.seller_id = s.seller_id
    LEFT JOIN 
        order_payments op ON o.order_id = op.order_id
    LEFT JOIN 
        order_reviews or_review ON o.order_id = or_review.order_id
    WHERE 
        o.order_status = 'delivered'
    ORDER BY 
        o.order_purchase_timestamp DESC
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
