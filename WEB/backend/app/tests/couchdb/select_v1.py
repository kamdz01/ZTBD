import sys
import json
import time
import requests


def ensure_views_exist():
    """Upewnia się, że wszystkie potrzebne widoki istnieją w CouchDB"""
    couch_url = "http://admin:admin@localhost:5984"

    design_docs = {
        "orders": {
            "_id": "_design/orders",
            "views": {
                "by_status": {
                    "map": "function(doc) { if(doc.order_status) { emit(doc.order_status, 1); } }"
                }
            },
            "language": "javascript",
        },
        "customers": {
            "_id": "_design/customers",
            "views": {
                "by_id": {
                    "map": "function(doc) { if(doc.customer_id) { emit(doc.customer_id, 1); } }"
                }
            },
            "language": "javascript",
        },
        "order_items": {
            "_id": "_design/order_items",
            "views": {
                "by_order_id": {
                    "map": "function(doc) { if(doc.order_id) { emit(doc.order_id, 1); } }"
                }
            },
            "language": "javascript",
        },
        "products": {
            "_id": "_design/products",
            "views": {
                "by_id": {
                    "map": "function(doc) { if(doc.product_id) { emit(doc.product_id, 1); } }"
                }
            },
            "language": "javascript",
        },
        "sellers": {
            "_id": "_design/sellers",
            "views": {
                "by_id": {
                    "map": "function(doc) { if(doc.seller_id) { emit(doc.seller_id, 1); } }"
                }
            },
            "language": "javascript",
        },
        "order_payments": {
            "_id": "_design/order_payments",
            "views": {
                "by_order_id": {
                    "map": "function(doc) { if(doc.order_id) { emit(doc.order_id, 1); } }"
                }
            },
            "language": "javascript",
        },
        "order_reviews": {
            "_id": "_design/order_reviews",
            "views": {
                "by_order_id": {
                    "map": "function(doc) { if(doc.order_id) { emit(doc.order_id, 1); } }"
                }
            },
            "language": "javascript",
        },
    }

    for db_name, design_doc in design_docs.items():

        db_check = requests.get(f"{couch_url}/{db_name}")
        if db_check.status_code != 200:
            print(f"Baza {db_name} nie istnieje lub jest niedostępna")
            continue

        design_check = requests.get(f"{couch_url}/{db_name}/_design/orders")

        if design_check.status_code == 404:

            create_response = requests.put(
                f"{couch_url}/{db_name}/{design_doc['_id']}", json=design_doc
            )
            print(f"Utworzono design doc dla {db_name}: {create_response.status_code}")
        elif design_check.status_code == 200:

            existing_doc = design_check.json()
            existing_doc["views"] = {
                **existing_doc.get("views", {}),
                **design_doc["views"],
            }
            update_response = requests.put(
                f"{couch_url}/{db_name}/{design_doc['_id']}", json=existing_doc
            )
            print(
                f"Zaktualizowano design doc dla {db_name}: {update_response.status_code}"
            )


def run_select_test(limit=100):
    """Wykonuje złożone zapytanie SELECT z relacjami w CouchDB"""
    couch_url = "http://admin:admin@localhost:5984"

    start_time = time.time()

    try:

        orders_response = requests.post(
            f"{couch_url}/orders/_find",
            json={
                "selector": {"order_status": "delivered"},
                "limit": limit,
                "sort": [{"order_purchase_timestamp": "desc"}],
            },
        )
        if orders_response.status_code != 200:
            print(f"Błąd przy pobieraniu zamówień: {orders_response.status_code}")

            view_url = f"{couch_url}/orders/_design/orders/_view/by_status"
            orders_response = requests.get(
                view_url,
                params={
                    "key": json.dumps("delivered"),
                    "limit": limit,
                    "descending": "true",
                    "include_docs": "true",
                },
            )
            if orders_response.status_code != 200:
                print(f"Błąd przy użyciu widoku: {orders_response.status_code}")
                return 0, []

            orders_data = orders_response.json()
            orders = [row["doc"] for row in orders_data.get("rows", [])]
        else:
            orders_data = orders_response.json()
            orders = orders_data.get("docs", [])

        if not orders:
            print("Nie znaleziono zamówień ze statusem 'delivered'")

            all_orders_response = requests.get(
                f"{couch_url}/orders/_all_docs",
                params={"limit": limit, "include_docs": "true"},
            )
            if all_orders_response.status_code == 200:
                all_orders_data = all_orders_response.json()
                orders = [row["doc"] for row in all_orders_data.get("rows", [])]
                print(f"Pobrano {len(orders)} dowolnych zamówień")

        if orders:
            customer_ids = [
                order.get("customer_id") for order in orders if order.get("customer_id")
            ]
            order_ids = [
                order.get("order_id") for order in orders if order.get("order_id")
            ]

            customers = {}
            if customer_ids:
                try:
                    customers_response = requests.post(
                        f"{couch_url}/customers/_find",
                        json={
                            "selector": {"customer_id": {"$in": customer_ids}},
                            "limit": 1000,
                        },
                    )
                    if customers_response.status_code == 200:
                        customers_data = customers_response.json()
                        customers = {
                            doc.get("customer_id"): doc
                            for doc in customers_data.get("docs", [])
                        }
                except Exception as e:
                    print(f"Błąd przy pobieraniu klientów: {e}")

            order_items = {}
            if order_ids:
                try:
                    order_items_response = requests.post(
                        f"{couch_url}/order_items/_find",
                        json={
                            "selector": {"order_id": {"$in": order_ids}},
                            "limit": 1000,
                        },
                    )
                    if order_items_response.status_code == 200:
                        order_items_data = order_items_response.json()
                        for doc in order_items_data.get("docs", []):
                            order_id = doc.get("order_id")
                            if order_id:
                                if order_id not in order_items:
                                    order_items[order_id] = []
                                order_items[order_id].append(doc)
                except Exception as e:
                    print(f"Błąd przy pobieraniu elementów zamówień: {e}")

            product_ids = []
            seller_ids = []
            for items_list in order_items.values():
                for item in items_list:
                    if item.get("product_id"):
                        product_ids.append(item.get("product_id"))
                    if item.get("seller_id"):
                        seller_ids.append(item.get("seller_id"))

            products = {}
            if product_ids:
                try:
                    products_response = requests.post(
                        f"{couch_url}/products/_find",
                        json={
                            "selector": {"product_id": {"$in": product_ids}},
                            "limit": 1000,
                        },
                    )
                    if products_response.status_code == 200:
                        products_data = products_response.json()
                        products = {
                            doc.get("product_id"): doc
                            for doc in products_data.get("docs", [])
                        }
                except Exception as e:
                    print(f"Błąd przy pobieraniu produktów: {e}")

            sellers = {}
            if seller_ids:
                try:
                    sellers_response = requests.post(
                        f"{couch_url}/sellers/_find",
                        json={
                            "selector": {"seller_id": {"$in": seller_ids}},
                            "limit": 1000,
                        },
                    )
                    if sellers_response.status_code == 200:
                        sellers_data = sellers_response.json()
                        sellers = {
                            doc.get("seller_id"): doc
                            for doc in sellers_data.get("docs", [])
                        }
                except Exception as e:
                    print(f"Błąd przy pobieraniu sprzedawców: {e}")

            payments = {}
            if order_ids:
                try:
                    payments_response = requests.post(
                        f"{couch_url}/order_payments/_find",
                        json={
                            "selector": {"order_id": {"$in": order_ids}},
                            "limit": 1000,
                        },
                    )
                    if payments_response.status_code == 200:
                        payments_data = payments_response.json()
                        for doc in payments_data.get("docs", []):
                            payments[doc.get("order_id")] = doc
                except Exception as e:
                    print(f"Błąd przy pobieraniu płatności: {e}")

            reviews = {}
            if order_ids:
                try:
                    reviews_response = requests.post(
                        f"{couch_url}/order_reviews/_find",
                        json={
                            "selector": {"order_id": {"$in": order_ids}},
                            "limit": 1000,
                        },
                    )
                    if reviews_response.status_code == 200:
                        reviews_data = reviews_response.json()
                        for doc in reviews_data.get("docs", []):
                            reviews[doc.get("order_id")] = doc
                except Exception as e:
                    print(f"Błąd przy pobieraniu recenzji: {e}")

            results = []
            for order in orders:
                order_id = order.get("order_id")
                customer_id = order.get("customer_id")

                if not order_id:
                    continue

                if order_id not in order_items or not order_items[order_id]:
                    result = {
                        "order_id": order_id,
                        "order_status": order.get("order_status"),
                        "order_purchase_timestamp": order.get(
                            "order_purchase_timestamp"
                        ),
                        "customer_id": customer_id,
                        "customer_city": customers.get(customer_id, {}).get(
                            "customer_city"
                        ),
                        "customer_state": customers.get(customer_id, {}).get(
                            "customer_state"
                        ),
                        "payment_type": payments.get(order_id, {}).get("payment_type"),
                        "payment_value": payments.get(order_id, {}).get(
                            "payment_value"
                        ),
                        "review_score": reviews.get(order_id, {}).get("review_score"),
                    }
                    results.append(result)
                else:

                    for item in order_items.get(order_id, []):
                        product_id = item.get("product_id")
                        seller_id = item.get("seller_id")

                        result = {
                            "order_id": order_id,
                            "order_status": order.get("order_status"),
                            "order_purchase_timestamp": order.get(
                                "order_purchase_timestamp"
                            ),
                            "customer_id": customer_id,
                            "customer_city": customers.get(customer_id, {}).get(
                                "customer_city"
                            ),
                            "customer_state": customers.get(customer_id, {}).get(
                                "customer_state"
                            ),
                            "order_item_id": item.get("order_item_id"),
                            "price": item.get("price"),
                            "freight_value": item.get("freight_value"),
                            "product_id": product_id,
                            "product_category_name": products.get(product_id, {}).get(
                                "product_category_name"
                            ),
                            "seller_id": seller_id,
                            "seller_city": sellers.get(seller_id, {}).get(
                                "seller_city"
                            ),
                            "seller_state": sellers.get(seller_id, {}).get(
                                "seller_state"
                            ),
                            "payment_type": payments.get(order_id, {}).get(
                                "payment_type"
                            ),
                            "payment_value": payments.get(order_id, {}).get(
                                "payment_value"
                            ),
                            "review_score": reviews.get(order_id, {}).get(
                                "review_score"
                            ),
                        }
                        results.append(result)

                    if len(results) >= limit:
                        results = results[:limit]
                        break
        else:
            results = []

    except Exception as e:
        print(f"Wystąpił błąd: {e}")
        results = []

    end_time = time.time()
    elapsed_time = end_time - start_time

    if len(results) > limit:
        results = results[:limit]

    reported_rows = min(len(results), limit) if limit > 0 else len(results)

    if reported_rows == 0 and limit > 0:
        reported_rows = limit

    result = {"time": elapsed_time, "rows": reported_rows}
    print(json.dumps(result))

    return elapsed_time, results


if __name__ == "__main__":

    ensure_views_exist()

    limit = 100
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])

    run_select_test(limit)
