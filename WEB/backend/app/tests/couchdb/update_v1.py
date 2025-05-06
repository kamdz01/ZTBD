import sys
import json
import time
import requests


def run_update_test(limit=None):
    # Sprawdź, w której bazie faktycznie masz dokumenty typu 'order', 'order_item', 'product'
    # Jeśli masz bazę "orders", użyj jej nazwy tutaj:
    db_name = "orders"
    couch_url = "http://admin:admin@localhost:5984"
    print(f"Połączenie z bazą CouchDB: {couch_url}/{db_name}")

    start_time = time.time()
    find_url = f"{couch_url}/{db_name}/_find"

    # 1. Zmieniamy zamówienia 'pending' -> 'delivered'
    find_pending_query = {"selector": {"type": "order", "order_status": "pending"}}
    pending_resp = requests.post(find_url, json=find_pending_query).json()
    pending_docs = pending_resp.get("docs", [])
    for doc in pending_docs:
        doc["order_status"] = "delivered"
        doc_url = f"{couch_url}/{db_name}/{doc['_id']}"
        requests.put(doc_url, json=doc)
    updated_orders = len(pending_docs)

    # 2. Aktualizujemy order_items powiązane z zamówieniami 'delivered'
    find_delivered = {"selector": {"type": "order", "order_status": "delivered"}}
    delivered_resp = requests.post(find_url, json=find_delivered).json()
    delivered_docs = delivered_resp.get("docs", [])
    delivered_ids = [x.get("order_id") for x in delivered_docs]

    order_items_to_update = []
    for order_id in delivered_ids:
        find_items_query = {
            "selector": {"type": "order_item", "order_id": order_id},
            "limit": 999999,
        }
        items_resp = requests.post(find_url, json=find_items_query).json()
        items_docs = items_resp.get("docs", [])
        for item_doc in items_docs:
            item_doc["shipping_limit_date"] = "2025-05-01 23:59:59"
            order_items_to_update.append(item_doc)
            item_url = f"{couch_url}/{db_name}/{item_doc['_id']}"
            requests.put(item_url, json=item_doc)
    updated_items = len(order_items_to_update)

    # 3. Zmiana kategorii produktów powiązanych z dostarczonymi zamówieniami
    product_ids = set(
        doc.get("product_id") for doc in order_items_to_update if "product_id" in doc
    )
    products_to_update = []
    for pid in product_ids:
        product_url = f"{couch_url}/{db_name}/{pid}"
        resp = requests.get(product_url)
        if resp.status_code == 200:
            product_doc = resp.json()
            product_doc["product_category_name"] = "home_appliances"
            products_to_update.append(product_doc)
            requests.put(product_url, json=product_doc)
    updated_products = len(products_to_update)

    # Podsumowanie
    elapsed_time = time.time() - start_time
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
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    run_update_test(limit)
