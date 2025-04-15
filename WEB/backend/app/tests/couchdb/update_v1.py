import sys
import json
import time
import requests


def run_update_test(limit=None):
    # Parametry połączenia
    couch_url = "http://admin:admin@localhost:5984"
    db_name = "ecommerce"
    print(f"Połączenie z bazą CouchDB: {couch_url}/{db_name}")

    # Start pomiaru czasu
    start_time = time.time()

    # 1. Update orders with status 'pending' to 'delivered'
    # Najpierw tworzymy tymczasowy widok by znaleźć zamówienia o statusie 'pending'
    pending_view = {
        "map": "function(doc) { if (doc.type === 'order' && doc.order_status === 'pending') { emit(doc._id, null); } }"
    }

    # Tworzymy tymczasowy widok
    temp_view_url = f"{couch_url}/{db_name}/_temp_view"
    response = requests.post(temp_view_url, json=pending_view)

    # Jeśli serwer nie obsługuje _temp_view, używamy Mango Query
    if response.status_code != 200:
        # Używamy Mango Query
        find_pending_query = {"selector": {"type": "order", "order_status": "pending"}}

        find_url = f"{couch_url}/{db_name}/_find"
        pending_results = requests.post(find_url, json=find_pending_query).json()

        pending_orders = []
        order_ids_delivered = []

        # Aktualizujemy znalezione zamówienia
        for doc in pending_results.get("docs", []):
            doc["order_status"] = "delivered"
            pending_orders.append(doc)
            order_ids_delivered.append(doc.get("order_id", ""))

            # Wykonujemy aktualizację
            doc_id = doc["_id"]
            update_url = f"{couch_url}/{db_name}/{doc_id}"
            requests.put(update_url, json=doc)
    else:
        # Używamy tymczasowego widoku
        pending_results = response.json()
        pending_orders = []
        order_ids_delivered = []

        for row in pending_results.get("rows", []):
            doc_id = row["id"]
            # Pobierz dokument
            doc_url = f"{couch_url}/{db_name}/{doc_id}"
            doc = requests.get(doc_url).json()

            # Aktualizuj status
            doc["order_status"] = "delivered"
            pending_orders.append(doc)
            order_ids_delivered.append(doc.get("order_id", ""))

            # Zapisz zaktualizowany dokument
            requests.put(doc_url, json=doc)

    # 2. Update order_items for orders that are delivered
    # Tworzymy widok dla znalezienia elementów zamówień
    order_items_view = {
        "map": "function(doc) { if (doc.type === 'order_item' && doc.order_id) { emit(doc.order_id, null); } }"
    }

    order_items_to_update = []

    # Dla każdego ID zamówienia, znajdź i aktualizuj elementy zamówienia
    for order_id in order_ids_delivered:
        # Używamy Mango Query zamiast tymczasowego widoku
        find_items_query = {"selector": {"type": "order_item", "order_id": order_id}}

        find_items_url = f"{couch_url}/{db_name}/_find"
        items_results = requests.post(find_items_url, json=find_items_query).json()

        for doc in items_results.get("docs", []):
            doc["shipping_limit_date"] = "2025-05-01 23:59:59"
            order_items_to_update.append(doc)

            # Aktualizuj dokument
            doc_id = doc["_id"]
            update_url = f"{couch_url}/{db_name}/{doc_id}"
            requests.put(update_url, json=doc)

    # 3. Update products based on order_items linked to delivered orders
    product_ids = set()

    # Dla każdego zamówienia, znajdź powiązane produkty
    for order_id in order_ids_delivered:
        # Używamy Mango Query do znalezienia powiązanych produktów
        find_products_query = {
            "selector": {"type": "order_item", "order_id": order_id},
            "fields": ["product_id"],
        }

        find_products_url = f"{couch_url}/{db_name}/_find"
        products_results = requests.post(
            find_products_url, json=find_products_query
        ).json()

        for doc in products_results.get("docs", []):
            if "product_id" in doc:
                product_ids.add(doc["product_id"])

    # Aktualizuj znalezione produkty
    products_to_update = []

    for product_id in product_ids:
        product_url = f"{couch_url}/{db_name}/{product_id}"
        response = requests.get(product_url)

        if response.status_code == 200:
            product_doc = response.json()
            product_doc["product_category_name"] = "home_appliances"
            products_to_update.append(product_doc)

            # Aktualizuj dokument
            requests.put(product_url, json=product_doc)

    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Zwracanie wyniku
    total_updated = (
        len(pending_orders) + len(order_items_to_update) + len(products_to_update)
    )
    result = {
        "time": elapsed_time,
        "rows": total_updated,
        "updated_orders": len(pending_orders),
        "updated_order_items": len(order_items_to_update),
        "updated_products": len(products_to_update),
    }
    print(json.dumps(result))

    return elapsed_time, total_updated


if __name__ == "__main__":
    # Pobranie limitu z argumentów (choć w tym przypadku limit nie jest używany)
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    run_update_test(limit)
