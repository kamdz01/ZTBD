import sys
import json
import time
import psycopg2
import psycopg2.extras


def run_update_test(limit=None):
    # Połączenie z PostgreSQL
    conn = psycopg2.connect(
        host="localhost", port=5432, database="mydb", user="admin", password="admin"
    )

    # Ustawienie kursora
    cursor = conn.cursor()

    # Start pomiaru czasu
    start_time = time.time()

    # 1. Update orders with status 'pending' to 'delivered'
    cursor.execute(
        """
        UPDATE orders
        SET order_status = 'delivered'
        WHERE order_status = 'pending'
        """
    )
    updated_orders = cursor.rowcount

    # 2. Update order_items for orders that are delivered
    cursor.execute(
        """
        UPDATE order_items
        SET shipping_limit_date = '2025-05-01 23:59:59'
        WHERE order_id IN (
            SELECT order_id
            FROM orders
            WHERE order_status = 'delivered'
        )
        """
    )
    updated_items = cursor.rowcount

    # 3. Update products for product_ids from order_items linked to delivered orders
    cursor.execute(
        """
        UPDATE products
        SET product_category_name = 'home_appliances'
        WHERE product_id IN (
            SELECT DISTINCT oi.product_id
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            WHERE o.order_status = 'delivered'
        )
        """
    )
    updated_products = cursor.rowcount

    # Zatwierdzenie zmian (bez jawnego rozpoczynania transakcji)
    conn.commit()

    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Zamknięcie połączenia
    cursor.close()
    conn.close()

    # Zwracanie wyniku
    total_updated = updated_orders + updated_items + updated_products
    result = {
        "time": elapsed_time,
        "rows": total_updated,
        "updated_orders": updated_orders,
        "updated_order_items": updated_items,
        "updated_products": updated_products,
    }
    print(json.dumps(result))

    return elapsed_time, total_updated


if __name__ == "__main__":
    # Pobranie limitu z argumentów (choć w tym przypadku limit nie jest używany)
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    run_update_test(limit)
