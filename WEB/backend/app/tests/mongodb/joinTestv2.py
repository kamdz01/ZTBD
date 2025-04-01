import sys
import json
import time
from pymongo import MongoClient


def run_join_test(limit=10):
    """
    Wykonuje złożone zapytanie z wieloma JOIN-ami i zwraca w JSON
    czas wykonania zapytania.
    """
    # Połączenie z MongoDB
    client = MongoClient("mongodb://admin:admin@localhost:27017/")
    db = client["olist"]

    # Rozpoczęcie pomiaru czasu
    start_time = time.time()

    # Złożona agregacja
    pipeline = [
        # Filtrowanie zamówień ze statusem 'delivered'
        {"$match": {"order_status": "delivered"}},
        
        # Sortowanie i limit
        {"$sort": {"order_purchase_timestamp": -1}},
        {"$limit": limit},
        
        # Łączenie z kolekcją customers
        {"$lookup": {
            "from": "customers",
            "localField": "customer_id",
            "foreignField": "customer_id",
            "as": "customer"
        }},
        {"$unwind": {"path": "$customer", "preserveNullAndEmptyArrays": True}},
        
        # Łączenie z kolekcją order_items
        {"$lookup": {
            "from": "order_items",
            "localField": "order_id",
            "foreignField": "order_id",
            "as": "order_items"
        }},
        {"$unwind": {"path": "$order_items", "preserveNullAndEmptyArrays": True}},
        
        # Łączenie z kolekcją products
        {"$lookup": {
            "from": "products",
            "localField": "order_items.product_id",
            "foreignField": "product_id",
            "as": "product"
        }},
        {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}},
        
        # Łączenie z kolekcją product_category_translation
        {"$lookup": {
            "from": "product_category_name_translation",
            "localField": "product.product_category_name",
            "foreignField": "product_category_name",
            "as": "product_category"
        }},
        {"$unwind": {"path": "$product_category", "preserveNullAndEmptyArrays": True}},
        
        # Łączenie z kolekcją sellers
        {"$lookup": {
            "from": "sellers",
            "localField": "order_items.seller_id",
            "foreignField": "seller_id",
            "as": "seller"
        }},
        {"$unwind": {"path": "$seller", "preserveNullAndEmptyArrays": True}},
        
        # Łączenie z kolekcją order_reviews
        {"$lookup": {
            "from": "order_reviews",
            "localField": "order_id",
            "foreignField": "order_id",
            "as": "review"
        }},
        {"$unwind": {"path": "$review", "preserveNullAndEmptyArrays": True}},
        
        # Projekcja wyniku
        {"$project": {
            "_id": 0,
            "order_id": 1,
            "customer_city": "$customer.customer_city",
            "customer_state": "$customer.customer_state",
            "seller_city": "$seller.seller_city",
            "seller_state": "$seller.seller_state",
            "product_category_name": "$product.product_category_name",
            "product_category_name_english": "$product_category.product_category_name_english",
            "review_score": "$review.review_score"
        }}
    ]

    results = list(db.orders.aggregate(pipeline, allowDiskUse=True))

    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Zamknięcie połączenia
    client.close()

    # Zwrócenie wyniku w formacie JSON
    result = {"time": elapsed_time}
    print(json.dumps(result))

    return elapsed_time


if __name__ == "__main__":
    # Domyślnie pobieramy 10 rekordów, chyba że podano inny limit w argumentach
    limit = 10
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    run_join_test(limit)