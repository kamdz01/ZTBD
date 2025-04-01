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

    # Agregacja dla grupowania według dnia
    pipeline = [
        {
            "$project": {
                "date": {
                    "$substr": [
                        "$order_purchase_timestamp",
                        0,
                        10,
                    ]  # Ekstrakcja daty (YYYY-MM-DD)
                }
            }
        },
        {"$group": {"_id": "$date", "order_count": {"$sum": 1}}},
        {"$project": {"_id": 0, "day": "$_id", "order_count": 1}},
        {"$sort": {"day": 1}},
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
