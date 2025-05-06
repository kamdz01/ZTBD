import requests
import time
import json


def setup_couchdb_partitioning():
    couch_url = "http://admin:admin@localhost:5984"

    # 1. Utworzenie zwykłej bazy
    requests.delete(f"{couch_url}/orders_no_partition")
    requests.put(f"{couch_url}/orders_no_partition")

    # 2. Utworzenie partycjonowanej bazy
    requests.delete(f"{couch_url}/orders_partitioned")
    requests.put(f"{couch_url}/orders_partitioned", json={"partitioned": True})

    # 3. Kopiowanie danych z istniejącej bazy do obu testowych baz
    # Najpierw do zwykłej
    all_docs = requests.get(f"{couch_url}/orders/_all_docs?include_docs=true").json()

    for row in all_docs.get("rows", []):
        if "doc" in row and "_id" in row["doc"]:
            doc = row["doc"]
            requests.put(f"{couch_url}/orders_no_partition/{doc['_id']}", json=doc)

    # Teraz do partycjonowanej (wymagane określenie klucza partycji)
    for row in all_docs.get("rows", []):
        if "doc" in row and "_id" in row["doc"]:
            doc = row["doc"]
            year = "2016"
            if "order_purchase_timestamp" in doc:
                timestamp = doc["order_purchase_timestamp"]
                if timestamp.startswith("2017"):
                    year = "2017"
                elif timestamp.startswith("2018"):
                    year = "2018"
            # W CouchDB 3.x partycjonowane dokumenty mają format "partition_key:doc_id"
            partition_id = f"{year}:{doc['_id']}"
            doc["_id"] = partition_id
            requests.put(f"{couch_url}/orders_partitioned/{partition_id}", json=doc)

    # 4. Dodanie indeksu
    requests.post(
        f"{couch_url}/orders_no_partition/_index",
        json={
            "index": {"fields": ["order_purchase_timestamp"]},
            "name": "timestamp_idx",
        },
    )
    requests.post(
        f"{couch_url}/orders_partitioned/_index",
        json={
            "index": {"fields": ["order_purchase_timestamp"]},
            "name": "timestamp_idx",
        },
    )

    return "Partycje w CouchDB zostały skonfigurowane"


def test_couchdb_partitioning():
    results = {"partition_test": {"with_partition": {}, "without_partition": {}}}
    couch_url = "http://admin:admin@localhost:5984"

    # Test bez partycjonowania
    start_time = time.time()
    query = {
        "selector": {
            "order_purchase_timestamp": {"$gte": "2017-01-01", "$lte": "2017-06-30"}
        }
    }
    response = requests.post(f"{couch_url}/orders_no_partition/_find", json=query)
    docs = response.json().get("docs", [])
    no_partition_time = time.time() - start_time
    results["partition_test"]["without_partition"]["time"] = no_partition_time
    results["partition_test"]["without_partition"]["rows"] = len(docs)

    # Test z partycjonowaniem (zapytanie tylko do odpowiedniej partycji)
    start_time = time.time()
    # W CouchDB 3.x możemy zapytać konkretną partycję
    response = requests.post(
        f"{couch_url}/orders_partitioned/_partition/2017/_find",
        json={
            "selector": {
                "order_purchase_timestamp": {"$gte": "2017-01-01", "$lte": "2017-06-30"}
            }
        },
    )
    docs = response.json().get("docs", [])
    partition_time = time.time() - start_time
    results["partition_test"]["with_partition"]["time"] = partition_time
    results["partition_test"]["with_partition"]["rows"] = len(docs)

    return results
