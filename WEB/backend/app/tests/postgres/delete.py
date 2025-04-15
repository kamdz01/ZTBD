import sys
import json
import time
import psycopg2
import psycopg2.extras


def run_delete_test(limit=None):
    """
    Test złożonego usuwania danych z wielu tabel w PostgreSQL.
    """
    # Połączenie z PostgreSQL
    conn = psycopg2.connect(
        host="localhost", port=5432, database="mydb", user="admin", password="admin"
    )

    # Ustawienie kursora
    cursor = conn.cursor()

    # Start pomiaru czasu
    start_time = time.time()

    try:
        # Rozpoczęcie transakcji
        cursor.execute("BEGIN TRANSACTION;")

        # Tworzenie tymczasowej tabeli przechowującej ID zamówień do usunięcia
        cursor.execute(
            """
        CREATE TEMPORARY TABLE orders_to_delete AS
        SELECT o.order_id
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        JOIN order_reviews r ON o.order_id = r.order_id
        LEFT JOIN order_payments p ON o.order_id = p.order_id
        WHERE o.order_purchase_timestamp < '2025-01-01'
          AND r.review_score < 3
          AND (p.payment_value < 100 OR p.payment_value IS NULL)
          AND c.customer_state IN ('SP', 'RJ')
          AND o.order_status IN ('canceled', 'unavailable');
        """
        )

        # Podliczenie liczby rekordów w tymczasowej tabeli
        cursor.execute("SELECT COUNT(*) FROM orders_to_delete;")
        orders_to_delete_count = cursor.fetchone()[0]

        # Usuwanie z order_reviews
        cursor.execute(
            """
        DELETE FROM order_reviews
        WHERE order_id IN (SELECT order_id FROM orders_to_delete);
        """
        )
        deleted_reviews = cursor.rowcount

        # Usuwanie z order_payments
        cursor.execute(
            """
        DELETE FROM order_payments
        WHERE order_id IN (SELECT order_id FROM orders_to_delete);
        """
        )
        deleted_payments = cursor.rowcount

        # Usuwanie z order_items (wraz z aktualizacją produktów)
        cursor.execute(
            """
        WITH deleted_items AS (
            DELETE FROM order_items
            WHERE order_id IN (SELECT order_id FROM orders_to_delete)
            RETURNING product_id
        )
        UPDATE products
        SET product_weight_g = product_weight_g * 0.9,
            product_photos_qty = product_photos_qty - 1
        WHERE product_id IN (SELECT DISTINCT product_id FROM deleted_items)
          AND product_photos_qty > 1;
        """
        )
        updated_products = cursor.rowcount

        # Pobieranie liczby usuniętych elementów zamówień (pośrednio)
        cursor.execute("SELECT COUNT(*) FROM orders_to_delete;")
        deleted_items_estimated = cursor.fetchone()[0] * 2  # Szacunkowa liczba

        # Usuwanie samych zamówień
        cursor.execute(
            """
        DELETE FROM orders
        WHERE order_id IN (SELECT order_id FROM orders_to_delete);
        """
        )
        deleted_orders = cursor.rowcount

        # Czyszczenie nieużywanych adresów klientów, którzy nie mają już zamówień
        cursor.execute(
            """
        DELETE FROM customers
        WHERE customer_id IN (
            SELECT c.customer_id
            FROM customers c
            LEFT JOIN orders o ON c.customer_id = o.customer_id
            WHERE o.order_id IS NULL
            AND c.customer_state IN ('SP', 'RJ')
        );
        """
        )
        deleted_customers = cursor.rowcount

        # Usuwanie tymczasowej tabeli
        cursor.execute("DROP TABLE orders_to_delete;")

        # Zatwierdzenie transakcji
        cursor.execute("COMMIT;")

    except Exception as e:
        # W przypadku błędu, wycofaj transakcję
        cursor.execute("ROLLBACK;")
        print(f"Error: {e}")
        raise

    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Zamknięcie połączenia
    cursor.close()
    conn.close()

    result = {
        "time": elapsed_time,
        "rows": deleted_orders,
    }
    print(json.dumps(result))

    return elapsed_time, deleted_orders


if __name__ == "__main__":
    # Pobranie limitu z argumentów (choć w tym przypadku limit nie jest używany)
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    run_delete_test(limit)
