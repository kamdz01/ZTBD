from pymongo import MongoClient
import time
import json


def setup_mongodb_partitioning():
    client = MongoClient("mongodb://admin:admin@localhost:27017/")
    db = client["ecommerce"]

    # 1. Utworzenie kolekcji bez partycjonowania
    if "orders_no_partition" in db.list_collection_names():
        db.orders_no_partition.drop()
    db.orders.aggregate([{"$match": {}}, {"$out": "orders_no_partition"}])

    # 2. Utworzenie kolekcji z partycjonowaniem czasowym
    if "orders_partitioned_2016" in db.list_collection_names():
        db.orders_partitioned_2016.drop()
    if "orders_partitioned_2017" in db.list_collection_names():
        db.orders_partitioned_2017.drop()
    if "orders_partitioned_2018" in db.list_collection_names():
        db.orders_partitioned_2018.drop()

    # Podział danych według lat
    db.orders.aggregate(
        [
            {
                "$match": {
                    "order_purchase_timestamp": {
                        "$gte": "2016-01-01",
                        "$lt": "2017-01-01",
                    }
                }
            },
            {"$out": "orders_partitioned_2016"},
        ]
    )
    db.orders.aggregate(
        [
            {
                "$match": {
                    "order_purchase_timestamp": {
                        "$gte": "2017-01-01",
                        "$lt": "2018-01-01",
                    }
                }
            },
            {"$out": "orders_partitioned_2017"},
        ]
    )
    db.orders.aggregate(
        [
            {
                "$match": {
                    "order_purchase_timestamp": {
                        "$gte": "2018-01-01",
                        "$lt": "2019-01-01",
                    }
                }
            },
            {"$out": "orders_partitioned_2018"},
        ]
    )

    # 3. Utworzenie indeksów
    db.orders_no_partition.create_index("order_purchase_timestamp")
    db.orders_partitioned_2016.create_index("order_purchase_timestamp")
    db.orders_partitioned_2017.create_index("order_purchase_timestamp")
    db.orders_partitioned_2018.create_index("order_purchase_timestamp")

    return "Partycje w MongoDB zostały skonfigurowane"


def test_mongodb_partitioning():
    results = {"partition_test": {"with_partition": {}, "without_partition": {}}}
    client = MongoClient("mongodb://admin:admin@localhost:27017/")
    db = client["ecommerce"]

    # Test bez partycjonowania
    start_time = time.time()
    count = db.orders_no_partition.count_documents(
        {"order_purchase_timestamp": {"$gte": "2017-01-01", "$lte": "2017-06-30"}}
    )
    no_partition_time = time.time() - start_time
    results["partition_test"]["without_partition"]["time"] = no_partition_time
    results["partition_test"]["without_partition"]["rows"] = count

    # Test z partycjonowaniem (zapytanie tylko do odpowiedniej kolekcji)
    start_time = time.time()
    count = db.orders_partitioned_2017.count_documents(
        {"order_purchase_timestamp": {"$gte": "2017-01-01", "$lte": "2017-06-30"}}
    )
    partition_time = time.time() - start_time
    results["partition_test"]["with_partition"]["time"] = partition_time
    results["partition_test"]["with_partition"]["rows"] = count

    return results
