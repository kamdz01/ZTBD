import sys
import json
import time
import requests


def run_select_test(limit=100):
    couch_url = "http://admin:admin@localhost:5984"
    start_time = time.time()
    design_doc = {
        "_id": "_design/orders",
        "views": {
            "daily_orders": {
                "map": "function(doc) { if (doc.order_purchase_timestamp) { emit(doc.order_purchase_timestamp.substring(0, 10), 1); } }",
                "reduce": "_count",
            }
        },
        "language": "javascript",
    }

    try:
        requests.put(f"{couch_url}/orders/_design/orders", json=design_doc)
    except Exception as e:

        pass

    view_url = f"{couch_url}/orders/_design/orders/_view/daily_orders"
    params = {"group": "true", "limit": limit}

    response = requests.get(view_url, params=params)
    data = response.json()

    results = []
    for row in data.get("rows", []):
        results.append({"day": row["key"], "order_count": row["value"]})

    end_time = time.time()
    elapsed_time = end_time - start_time

    result = {"time": elapsed_time, "rows": len(results)}
    print(json.dumps(result))

    return elapsed_time, results


if __name__ == "__main__":

    limit = 100
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    run_select_test(limit)
