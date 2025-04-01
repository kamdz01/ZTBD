import sys
import json
import time
from pymongo import MongoClient


def run_join_test():
    # Połączenie z MongoDB
    client = MongoClient("mongodb://admin:admin@localhost:27017/")
    db = client["ecommerce"]

    # Start pomiaru czasu
    start_time = time.time()

    # Agregacja dla klientów z co najmniej 2 zatwierdzonymi zamówieniami
    pipeline = [
        # Filtracja zamówień ze statusem 'approved'
        {"$match": {"order_status": "approved"}},
        # Grupowanie wg customer_id i zliczanie liczby zamówień
        {
            "$group": {
                "_id": "$customer_id",
                "total_orders": {"$sum": 1},
                "last_order_purchase_timestamp": {"$max": "$order_purchase_timestamp"},
            }
        },
        # Filtrowanie klientów z co najmniej 2 zamówieniami
        {"$match": {"total_orders": {"$gte": 1}}},
        # Łączenie z kolekcją customers
        {
            "$lookup": {
                "from": "customers",
                "localField": "_id",
                "foreignField": "customer_id",
                "as": "customer_info",
            }
        },
        # Rozwinięcie tablicy customer_info
        {"$unwind": "$customer_info"},
        # Projekcja wyniku
        {
            "$project": {
                "_id": 0,
                "customer_id": "$_id",
                "customer_city": "$customer_info.customer_city",
                "total_orders": 1,
                "last_order_purchase_timestamp": 1,
            }
        },
        # Sortowanie po dacie ostatniego zamówienia malejąco
        {"$sort": {"last_order_purchase_timestamp": -1}},
    ]

    results = list(db.orders.aggregate(pipeline, allowDiskUse=True))
    row_count = len(results)

    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Zamknięcie połączenia
    client.close()

    # Zwrócenie wyniku w formacie JSON
    result = {"time": elapsed_time, "rows": row_count}
    print(json.dumps(result))

    return elapsed_time, results


if __name__ == "__main__":
    run_join_test()
