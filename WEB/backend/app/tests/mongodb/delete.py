import sys
import json
import time
from pymongo import MongoClient
from datetime import datetime


def run_delete_test(limit=None):
    """
    Test złożonego usuwania danych z wielu kolekcji w MongoDB.
    """
    # Połączenie z MongoDB
    client = MongoClient("mongodb://admin:admin@localhost:27017/")
    db = client["ecommerce"]

    # Start pomiaru czasu
    start_time = time.time()

    # Dodatkowe informacje debugowania
    print("Rozpoczynanie testu usuwania dla MongoDB")

    # Sprawdzanie nazw kolekcji
    collections = db.list_collection_names()
    print(f"Dostępne kolekcje: {collections}")

    try:
        # Rozdzielam złożoną agregację na proste etapy dla lepszego debugowania

        # 1. Najpierw znajdź zamówienia ze statusem canceled/unavailable
        status_filter = {"order_status": {"$in": ["canceled", "unavailable"]}}

        # Dodaj warunek daty, próbując różne formaty
        date_filter = {"order_purchase_timestamp": {"$lt": "2025-01-01T00:00:00.000Z"}}

        # Łączne filtry dla zamówień
        orders_filter = {"$and": [status_filter, date_filter]}

        # Pobierz wszystkie zamówienia spełniające początkowe warunki
        potential_orders = list(
            db.orders.find(orders_filter, {"_id": 1, "order_id": 1, "customer_id": 1})
        )
        print(
            f"Znaleziono {len(potential_orders)} potencjalnych zamówień (status + data)"
        )

        if not potential_orders:
            print("Nie znaleziono zamówień spełniających bazowe kryteria")
            return 0, 0

        # Wyciągnij ID zamówień i klientów
        initial_order_ids = [
            order["order_id"] for order in potential_orders if "order_id" in order
        ]
        customer_ids = [
            order["customer_id"] for order in potential_orders if "customer_id" in order
        ]

        print(f"Unikalne ID zamówień: {len(set(initial_order_ids))}")
        print(f"Unikalne ID klientów: {len(set(customer_ids))}")

        # 2. Filtruj po stanach klientów (SP, RJ)
        customers_filter = {
            "customer_id": {"$in": customer_ids},
            "customer_state": {"$in": ["SP", "RJ"]},
        }

        valid_customers = list(
            db.customers.find(customers_filter, {"_id": 1, "customer_id": 1})
        )
        valid_customer_ids = [customer["customer_id"] for customer in valid_customers]

        print(f"Klienci ze stanów SP/RJ: {len(valid_customer_ids)}")

        # 3. Filtruj zamówienia tylko dla tych klientów
        filtered_orders = [
            order
            for order in potential_orders
            if order.get("customer_id") in valid_customer_ids
        ]
        filtered_order_ids = [order["order_id"] for order in filtered_orders]

        print(f"Zamówienia po filtrowaniu klientów: {len(filtered_order_ids)}")

        # 4. Filtruj po niskich ocenach (< 3)
        reviews_filter = {
            "order_id": {"$in": filtered_order_ids},
            "review_score": {"$lt": "3"},
        }

        low_score_reviews = list(
            db.order_reviews.find(reviews_filter, {"_id": 1, "order_id": 1})
        )
        low_score_order_ids = [review["order_id"] for review in low_score_reviews]

        print(f"Zamówienia z oceną < 3: {len(low_score_order_ids)}")

        # 5. Filtruj po wartości płatności (< 100 lub brak płatności)
        payment_filter = {
            "order_id": {"$in": low_score_order_ids},
            "$expr": {
                "$lt": [{"$toDouble": "$payment_value"}, 100.0]
            },  # Convert string to number during comparison
        }

        low_payment_orders = list(
            db.order_payments.find(payment_filter, {"_id": 1, "order_id": 1})
        )
        low_payment_order_ids = [payment["order_id"] for payment in low_payment_orders]

        # Znajdź zamówienia bez płatności
        all_payments_cursor = db.order_payments.find(
            {"order_id": {"$in": low_score_order_ids}}, {"_id": 0, "order_id": 1}
        )
        all_payments = [payment["order_id"] for payment in all_payments_cursor]

        # Identyfikuj zamówienia bez płatności
        orders_without_payments = [
            order_id for order_id in low_score_order_ids if order_id not in all_payments
        ]
        # Połącz listy zamówień z niską płatnością i bez płatności
        final_order_ids = list(set(low_payment_order_ids + orders_without_payments))

        print(f"Ostateczna liczba zamówień do usunięcia: {len(final_order_ids)}")

        if not final_order_ids:
            print("Brak zamówień spełniających wszystkie kryteria")
            return 0, 0

        # Znajdź ID produktów do aktualizacji
        product_ids_cursor = db.order_items.distinct(
            "product_id", {"order_id": {"$in": final_order_ids}}
        )
        product_ids = list(product_ids_cursor)

        print(f"Znaleziono {len(product_ids)} produktów do aktualizacji")

        # Usuwanie recenzji
        delete_reviews_result = db.order_reviews.delete_many(
            {"order_id": {"$in": final_order_ids}}
        )
        deleted_reviews = delete_reviews_result.deleted_count
        print(f"Usunięto {deleted_reviews} recenzji")

        # Usuwanie płatności
        delete_payments_result = db.order_payments.delete_many(
            {"order_id": {"$in": final_order_ids}}
        )
        deleted_payments = delete_payments_result.deleted_count
        print(f"Usunięto {deleted_payments} płatności")

        # Usuwanie elementów zamówień
        delete_items_result = db.order_items.delete_many(
            {"order_id": {"$in": final_order_ids}}
        )
        deleted_items = delete_items_result.deleted_count
        print(f"Usunięto {deleted_items} elementów zamówień")

        # Aktualizacja produktów
        # updated_products = 0
        # for product_id in product_ids:
        #     update_result = db.products.update_one(
        #         {"product_id": product_id, "product_photos_qty": {"$gt": 1}},
        #         {
        #             "$mul": {"product_weight_g": 0.9},
        #             "$inc": {"product_photos_qty": -1},
        #         },
        #     )
        #     updated_products += update_result.modified_count
        # print(f"Zaktualizowano {updated_products} produktów")

        # Usunięcie zamówień
        delete_orders_result = db.orders.delete_many(
            {"order_id": {"$in": final_order_ids}}
        )
        deleted_orders = delete_orders_result.deleted_count
        print(f"Usunięto {deleted_orders} zamówień")

        # Znajdź klientów bez zamówień po usunięciu
        # Wykonuję dwa zapytania zamiast jednej agregacji
        # remaining_orders = list(db.orders.find({}, {"_id": 0, "customer_id": 1}))
        # remaining_customer_ids = [order["customer_id"] for order in remaining_orders]

        # # Znajdź klientów ze stanów SP, RJ którzy nie mają zamówień
        # orphaned_customers = db.customers.find(
        #     {
        #         "customer_state": {"$in": ["SP", "RJ"]},
        #         "customer_id": {"$nin": remaining_customer_ids},
        #     }
        # )
        # orphaned_customer_ids = [
        #     customer["customer_id"] for customer in orphaned_customers
        # ]

        # # Usuń osieroconych klientów
        # delete_customers_result = db.customers.delete_many(
        #     {"customer_id": {"$in": orphaned_customer_ids}}
        # )
        # deleted_customers = delete_customers_result.deleted_count
        # print(f"Usunięto {deleted_customers} klientów")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        raise

    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Zamknięcie połączenia
    client.close()

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
