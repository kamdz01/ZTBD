import sys
import json
import time
from pymongo import MongoClient


def run_update_test(limit=None):
    # Połączenie z MongoDB
    client = MongoClient("mongodb://admin:admin@localhost:27017/")
    db = client["ecommerce"]

    # Start pomiaru czasu
    start_time = time.time()

    # 1. Update orders with status 'pending' to 'delivered'
    orders_result = db.orders.update_many(
        {"order_status": "pending"}, {"$set": {"order_status": "delivered"}}
    )

    # Get IDs of updated orders
    updated_order_ids = [
        doc["order_id"] for doc in db.orders.find({"order_status": "delivered"})
    ]

    # 2. Update order_items for orders that are delivered
    items_result = db.order_items.update_many(
        {"order_id": {"$in": updated_order_ids}},
        {"$set": {"shipping_limit_date": "2025-05-01 23:59:59"}},
    )

    # 3. Find distinct product IDs from order_items linked to delivered orders
    pipeline = [
        {"$match": {"order_id": {"$in": updated_order_ids}}},
        {"$group": {"_id": "$product_id"}},
    ]

    product_ids = [doc["_id"] for doc in db.order_items.aggregate(pipeline)]

    # Update products with those IDs
    products_result = db.products.update_many(
        {"_id": {"$in": product_ids}},
        {"$set": {"product_category_name": "home_appliances"}},
    )

    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Zamknięcie połączenia
    client.close()

    # Zwracanie wyniku
    total_updated = (
        orders_result.modified_count
        + items_result.modified_count
        + products_result.modified_count
    )
    result = {
        "time": elapsed_time,
        "rows": total_updated,
        "updated_orders": orders_result.modified_count,
        "updated_order_items": items_result.modified_count,
        "updated_products": products_result.modified_count,
    }
    print(json.dumps(result))

    return elapsed_time, total_updated


if __name__ == "__main__":
    # Pobranie limitu z argumentów (choć w tym przypadku limit nie jest używany)
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    run_update_test(limit)
