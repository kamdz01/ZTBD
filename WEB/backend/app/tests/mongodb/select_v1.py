import sys
import json
import time
from pymongo import MongoClient


def run_select_test(limit=100):
    client = MongoClient("mongodb://admin:admin@localhost:27017/")
    db = client["ecommerce"]

    # Tworzenie indeksów w celu przyspieszenia zapytania
    try:
        db.orders.create_index("order_status")
        db.orders.create_index("order_id")
        db.customers.create_index("customer_id")
        db.order_items.create_index("order_id")
        db.products.create_index("product_id")
        db.sellers.create_index("seller_id")
        db.order_payments.create_index("order_id")
        db.order_reviews.create_index("order_id")
    except Exception as e:
        print(f"Ostrzeżenie: Nie można utworzyć indeksów: {e}")

    # Start pomiaru czasu
    start_time = time.time()

    # Zoptymalizowana agregacja - najpierw filtrowanie i limit, potem złączenia
    pipeline = [
        # Filtrowanie na samym początku
        {"$match": {"order_status": "delivered"}},
        # Sortowanie i limit przed drogimi operacjami
        {"$sort": {"order_purchase_timestamp": -1}},
        {"$limit": limit},
        # Dalsze operacje na mniejszym zbiorze danych
        {
            "$lookup": {
                "from": "customers",
                "localField": "customer_id",
                "foreignField": "customer_id",
                "as": "customer",
            }
        },
        {"$unwind": {"path": "$customer", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "order_items",
                "localField": "order_id",
                "foreignField": "order_id",
                "as": "items",
            }
        },
        {"$unwind": {"path": "$items", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "products",
                "localField": "items.product_id",
                "foreignField": "product_id",
                "as": "product",
            }
        },
        {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "sellers",
                "localField": "items.seller_id",
                "foreignField": "seller_id",
                "as": "seller",
            }
        },
        {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "order_payments",
                "localField": "order_id",
                "foreignField": "order_id",
                "as": "payment",
            }
        },
        {
            "$lookup": {
                "from": "order_reviews",
                "localField": "order_id",
                "foreignField": "order_id",
                "as": "review",
            }
        },
        {
            "$project": {
                "order_id": 1,
                "order_status": 1,
                "order_purchase_timestamp": 1,
                "customer_id": "$customer.customer_id",
                "customer_city": "$customer.customer_city",
                "customer_state": "$customer.customer_state",
                "order_item_id": "$items.order_item_id",
                "price": "$items.price",
                "freight_value": "$items.freight_value",
                "product_id": "$product.product_id",
                "product_category_name": "$product.product_category_name",
                "seller_id": "$seller.seller_id",
                "seller_city": "$seller.seller_city",
                "seller_state": "$seller.seller_state",
                "payment_type": {"$arrayElemAt": ["$payment.payment_type", 0]},
                "payment_value": {"$arrayElemAt": ["$payment.payment_value", 0]},
                "review_score": {"$arrayElemAt": ["$review.review_score", 0]},
            }
        },
    ]

    # Użycie allowDiskUse, aby umożliwić wykorzystanie dysku przy dużych danych
    results = list(db.orders.aggregate(pipeline, allowDiskUse=True))

    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Zamknięcie połączenia
    client.close()

    # Zwracanie wyniku
    result = {"time": elapsed_time, "rows": len(results)}
    print(json.dumps(result))

    return elapsed_time, results


if __name__ == "__main__":
    # Pobranie limitu z argumentów
    limit = 100  # domyślnie
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    run_select_test(limit)
