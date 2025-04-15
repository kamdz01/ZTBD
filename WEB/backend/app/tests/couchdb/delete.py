import sys
import json
import time
import requests
import random


def run_delete_test(limit=None):
    """
    Test złożonego usuwania danych z wielu baz w CouchDB.
    """
    # Parametry połączenia
    couch_url = "http://admin:admin@localhost:5984"
    print(f"Połączenie z CouchDB: {couch_url}")

    # Start pomiaru czasu
    start_time = time.time()

    # Inicjalizacja liczników
    deleted_reviews = 0
    deleted_payments = 0
    deleted_items = 0
    deleted_orders = 0
    updated_products = 0
    deleted_customers = 0

    # Dodatkowe informacje debugowania
    print("Rozpoczynanie testu usuwania dla CouchDB")

    try:
        # 1. Najpierw znajdź zamówienia ze statusem canceled/unavailable
        orders_query = {
            "selector": {
                "$and": [
                    {"order_status": {"$in": ["canceled", "unavailable"]}},
                    {"order_purchase_timestamp": {"$lt": "2025-01-01"}},
                ],
            },
            "fields": ["_id", "_rev", "order_id", "customer_id"],
            "limit": 1000000,
        }

        find_orders_url = f"{couch_url}/orders/_find"
        orders_response = requests.post(find_orders_url, json=orders_query)

        if orders_response.status_code != 200:
            print(f"Błąd przy wyszukiwaniu zamówień: {orders_response.status_code}")
            print(orders_response.text)

            # Sprawdźmy czy bazy istnieją
            all_dbs_response = requests.get(f"{couch_url}/_all_dbs")
            if all_dbs_response.status_code == 200:
                databases = all_dbs_response.json()
                print(f"Dostępne bazy danych: {databases}")

                # Jeśli potrzebnych baz nie ma, wstaw testowe dane
                missing_dbs = []
                required_dbs = [
                    "customers",
                    "orders",
                    "order_reviews",
                    "order_payments",
                    "order_items",
                    "products",
                ]
                for db in required_dbs:
                    if db not in databases:
                        missing_dbs.append(db)
                        # Tworzenie baz danych
                        requests.put(f"{couch_url}/{db}")

                if missing_dbs:
                    print(f"Utworzono brakujące bazy danych: {missing_dbs}")

                # Ponów zapytanie
                orders_response = requests.post(find_orders_url, json=orders_query)
                if orders_response.status_code != 200:
                    print("Nadal problem z zapytaniem po wstawieniu danych")
                    return 0, 0
            else:
                print("Problem z listowaniem baz danych")
                return 0, 0

        potential_orders = orders_response.json().get("docs", [])
        print(
            f"Znaleziono {len(potential_orders)} potencjalnych zamówień (status + data)"
        )

        if not potential_orders:
            print("Nie znaleziono zamówień spełniających bazowe kryteria")
            print("Wstawianie testowych danych...")
            insert_test_data(couch_url)
            # Ponów zapytanie
            orders_response = requests.post(find_orders_url, json=orders_query)
            potential_orders = orders_response.json().get("docs", [])
            if not potential_orders:
                print("Nadal brak zamówień - przerywam test")
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
        # Wyszukiwanie klientów ze stanów SP i RJ
        customers_query = {
            "selector": {
                "customer_id": {"$in": customer_ids},
                "customer_state": {"$in": ["SP", "RJ"]},
            },
            "fields": ["customer_id"],
            "limit": 1000000,
        }

        find_customers_url = f"{couch_url}/customers/_find"
        customers_response = requests.post(find_customers_url, json=customers_query)

        if customers_response.status_code != 200:
            print(f"Błąd przy wyszukiwaniu klientów: {customers_response.status_code}")
            print(customers_response.text)
            return 0, 0

        valid_customers = customers_response.json().get("docs", [])
        valid_customer_ids = [customer["customer_id"] for customer in valid_customers]

        print(f"Klienci ze stanów SP/RJ: {len(valid_customer_ids)}")

        # 3. Filtruj zamówienia tylko dla tych klientów
        filtered_orders = [
            order
            for order in potential_orders
            if "customer_id" in order and order["customer_id"] in valid_customer_ids
        ]
        filtered_order_ids = [order["order_id"] for order in filtered_orders]

        print(f"Zamówienia po filtrowaniu klientów: {len(filtered_order_ids)}")

        if not filtered_order_ids:
            print("Brak zamówień po filtrowaniu klientów")
            return 0, 0

        # 4. Filtruj po niskich ocenach (< 3)
        # Ponieważ CouchDB ma limity na wielkość zapytań, możemy potrzebować podzielić to na partie
        all_low_score_orders = []
        batch_size = 50

        for i in range(0, len(filtered_order_ids), batch_size):
            batch = filtered_order_ids[i : i + batch_size]
            reviews_query = {
                "selector": {
                    "order_id": {"$in": batch},
                    "review_score": {"$lt": "3"},
                },
                "fields": ["order_id"],
            }

            reviews_response = requests.post(
                f"{couch_url}/order_reviews/_find", json=reviews_query
            )

            if reviews_response.status_code != 200:
                print(
                    f"Błąd przy wyszukiwaniu recenzji: {reviews_response.status_code}"
                )
                print(reviews_response.text)
                continue

            batch_results = reviews_response.json().get("docs", [])
            all_low_score_orders.extend(
                [review["order_id"] for review in batch_results]
            )

        low_score_order_ids = list(set(all_low_score_orders))
        print(f"Zamówienia z oceną < 3: {len(low_score_order_ids)}")

        if not low_score_order_ids:
            print("Brak zamówień z niską oceną")
            return 0, 0

        # 5. Filtruj po wartości płatności (< 100 lub brak płatności)
        # Znajdź zamówienia z płatnościami < 100
        all_low_payment_orders = []

        for i in range(0, len(low_score_order_ids), batch_size):
            batch = low_score_order_ids[i : i + batch_size]
            payments_query = {
                "selector": {
                    "order_id": {"$in": batch},
                    "payment_value": {"$lt": "100.00"},  # Zmieniono na string
                },
                "fields": ["order_id"],
            }

            payments_response = requests.post(
                f"{couch_url}/order_payments/_find", json=payments_query
            )

            if payments_response.status_code != 200:
                print(
                    f"Błąd przy wyszukiwaniu płatności: {payments_response.status_code}"
                )
                print(payments_response.text)
                continue

            batch_results = payments_response.json().get("docs", [])
            all_low_payment_orders.extend(
                [payment["order_id"] for payment in batch_results]
            )

        # Znajdź wszystkie zamówienia, które mają płatności
        all_payments = []

        for i in range(0, len(low_score_order_ids), batch_size):
            batch = low_score_order_ids[i : i + batch_size]
            all_payments_query = {
                "selector": {"order_id": {"$in": batch}},
                "fields": ["order_id"],
            }

            all_payments_response = requests.post(
                f"{couch_url}/order_payments/_find", json=all_payments_query
            )

            if all_payments_response.status_code != 200:
                print(
                    f"Błąd przy wyszukiwaniu wszystkich płatności: {all_payments_response.status_code}"
                )
                print(all_payments_response.text)
                continue

            batch_results = all_payments_response.json().get("docs", [])
            all_payments.extend([payment["order_id"] for payment in batch_results])

        # Zamówienia bez płatności
        orders_without_payments = [
            order_id for order_id in low_score_order_ids if order_id not in all_payments
        ]

        # Połącz listy zamówień z niską płatnością i bez płatności
        final_order_ids = list(set(all_low_payment_orders + orders_without_payments))

        print(f"Zamówienia z płatnością < 100: {len(all_low_payment_orders)}")
        print(f"Zamówienia bez płatności: {len(orders_without_payments)}")
        print(f"Ostateczna liczba zamówień do usunięcia: {len(final_order_ids)}")

        if not final_order_ids:
            print("Brak zamówień spełniających wszystkie kryteria")
            return 0, 0

        # Teraz wykonujemy usuwanie i aktualizacje
        # Dla każdego zamówienia musimy znaleźć i usunąć powiązane dokumenty

        # Znajdź ID produktów z elementów zamówień
        all_product_ids = set()

        for i in range(0, len(final_order_ids), batch_size):
            batch = final_order_ids[i : i + batch_size]
            items_query = {
                "selector": {"order_id": {"$in": batch}},
                "fields": ["product_id"],
            }

            items_response = requests.post(
                f"{couch_url}/order_items/_find", json=items_query
            )

            if items_response.status_code != 200:
                print(
                    f"Błąd przy wyszukiwaniu elementów zamówień: {items_response.status_code}"
                )
                print(items_response.text)
                continue

            batch_results = items_response.json().get("docs", [])
            for item in batch_results:
                if "product_id" in item:
                    all_product_ids.add(item["product_id"])

        print(f"Znaleziono {len(all_product_ids)} produktów do aktualizacji")

        # Usuwanie recenzji
        for i in range(0, len(final_order_ids), batch_size):
            batch = final_order_ids[i : i + batch_size]
            reviews_to_delete_query = {
                "selector": {"order_id": {"$in": batch}},
                "fields": ["_id", "_rev"],
            }

            reviews_to_delete_response = requests.post(
                f"{couch_url}/order_reviews/_find", json=reviews_to_delete_query
            )

            if reviews_to_delete_response.status_code != 200:
                print(
                    f"Błąd przy wyszukiwaniu recenzji do usunięcia: {reviews_to_delete_response.status_code}"
                )
                print(reviews_to_delete_response.text)
                continue

            reviews_to_delete = reviews_to_delete_response.json().get("docs", [])

            for review in reviews_to_delete:
                doc_id = review["_id"]
                doc_rev = review["_rev"]
                delete_url = f"{couch_url}/order_reviews/{doc_id}?rev={doc_rev}"
                delete_response = requests.delete(delete_url)

                if delete_response.status_code == 200:
                    deleted_reviews += 1

        print(f"Usunięto {deleted_reviews} recenzji")

        # Usuwanie płatności
        for i in range(0, len(final_order_ids), batch_size):
            batch = final_order_ids[i : i + batch_size]
            payments_to_delete_query = {
                "selector": {"order_id": {"$in": batch}},
                "fields": ["_id", "_rev"],
            }

            payments_to_delete_response = requests.post(
                f"{couch_url}/order_payments/_find", json=payments_to_delete_query
            )

            if payments_to_delete_response.status_code != 200:
                print(
                    f"Błąd przy wyszukiwaniu płatności do usunięcia: {payments_to_delete_response.status_code}"
                )
                print(payments_to_delete_response.text)
                continue

            payments_to_delete = payments_to_delete_response.json().get("docs", [])

            for payment in payments_to_delete:
                doc_id = payment["_id"]
                doc_rev = payment["_rev"]
                delete_url = f"{couch_url}/order_payments/{doc_id}?rev={doc_rev}"
                delete_response = requests.delete(delete_url)

                if delete_response.status_code == 200:
                    deleted_payments += 1

        print(f"Usunięto {deleted_payments} płatności")

        # Usuwanie elementów zamówień
        for i in range(0, len(final_order_ids), batch_size):
            batch = final_order_ids[i : i + batch_size]
            items_to_delete_query = {
                "selector": {"order_id": {"$in": batch}},
                "fields": ["_id", "_rev"],
            }

            items_to_delete_response = requests.post(
                f"{couch_url}/order_items/_find", json=items_to_delete_query
            )

            if items_to_delete_response.status_code != 200:
                print(
                    f"Błąd przy wyszukiwaniu elementów zamówień do usunięcia: {items_to_delete_response.status_code}"
                )
                print(items_to_delete_response.text)
                continue

            items_to_delete = items_to_delete_response.json().get("docs", [])

            for item in items_to_delete:
                doc_id = item["_id"]
                doc_rev = item["_rev"]
                delete_url = f"{couch_url}/order_items/{doc_id}?rev={doc_rev}"
                delete_response = requests.delete(delete_url)

                if delete_response.status_code == 200:
                    deleted_items += 1

        print(f"Usunięto {deleted_items} elementów zamówień")

        # Usuwanie zamówień
        for i in range(0, len(final_order_ids), batch_size):
            batch = final_order_ids[i : i + batch_size]
            orders_to_delete_query = {
                "selector": {"order_id": {"$in": batch}},
                "fields": ["_id", "_rev"],
            }

            orders_to_delete_response = requests.post(
                f"{couch_url}/orders/_find", json=orders_to_delete_query
            )

            if orders_to_delete_response.status_code != 200:
                print(
                    f"Błąd przy wyszukiwaniu zamówień do usunięcia: {orders_to_delete_response.status_code}"
                )
                print(orders_to_delete_response.text)
                continue

            orders_to_delete = orders_to_delete_response.json().get("docs", [])

            for order in orders_to_delete:
                doc_id = order["_id"]
                doc_rev = order["_rev"]
                delete_url = f"{couch_url}/orders/{doc_id}?rev={doc_rev}"
                delete_response = requests.delete(delete_url)

                if delete_response.status_code == 200:
                    deleted_orders += 1

        print(f"Usunięto {deleted_orders} zamówień")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 0, 0

    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Zwracanie wyniku
    result = {"time": elapsed_time, "rows": deleted_orders}
    print(json.dumps(result))

    return elapsed_time, deleted_orders


if __name__ == "__main__":
    # Pobranie limitu z argumentów (choć w tym przypadku limit nie jest używany)
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    run_delete_test(limit)
