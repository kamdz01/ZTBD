import sys
import json
import time
from pymongo import MongoClient


def run_select_test(limit=100):
    # Połączenie z MongoDB
    client = MongoClient("mongodb://admin:admin@localhost:27017/")
    db = client["olist"]

    # Start pomiaru czasu
    start_time = time.time()

    # Agregacja z operacjami $lookup (odpowiednik JOIN)
    pipeline = [
        {"$match": {"order_status": "delivered"}},
        {
            "$lookup": {
                "from": "customers",
                "localField": "customer_id",
                "foreignField": "customer_id",
                "as": "customer",
            }
        },
        {"$unwind": "$customer"},
        {
            "$lookup": {
                "from": "order_items",
                "localField": "order_id",
                "foreignField": "order_id",
                "as": "items",
            }
        },
        {"$unwind": "$items"},
        {
            "$lookup": {
                "from": "products",
                "localField": "items.product_id",
                "foreignField": "product_id",
                "as": "product",
            }
        },
        {"$unwind": "$product"},
        {
            "$lookup": {
                "from": "sellers",
                "localField": "items.seller_id",
                "foreignField": "seller_id",
                "as": "seller",
            }
        },
        {"$unwind": "$seller"},
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
        {"$sort": {"order_purchase_timestamp": -1}},
        {"$limit": limit},
    ]

    results = list(db.orders.aggregate(pipeline))

    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Zamknięcie połączenia
    client.close()

    # Zwracanie wyniku
    result = {"time": elapsed_time, "count": len(results)}
    print(json.dumps(result))

    return elapsed_time


if __name__ == "__main__":
    # Pobranie limitu z argumentów
    limit = 100  # domyślnie
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    run_select_test(limit)
