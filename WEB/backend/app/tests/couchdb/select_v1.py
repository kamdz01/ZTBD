import sys
import json
import time
import requests


def run_select_test(limit=100):

    couch_url = "http://admin:admin@localhost:5984"

    start_time = time.time()

    view_url = f"{couch_url}/orders/_design/orders/_view/by_status"
    params = {
        "key": json.dumps("delivered"),
        "limit": limit,
        "descending": "true",
        "include_docs": "true",
    }

    orders_response = requests.get(view_url, params=params)
    orders_data = orders_response.json()
    orders = [row["doc"] for row in orders_data.get("rows", [])]

    customer_ids = [order.get("customer_id") for order in orders]
    order_ids = [order.get("order_id") for order in orders]

    customers_response = requests.post(
        f"{couch_url}/customers/_design/customers/_view/by_id",
        json={"keys": customer_ids, "include_docs": True},
    )
    customers_data = customers_response.json()
    customers = {row["key"]: row["doc"] for row in customers_data.get("rows", [])}

    order_items_response = requests.post(
        f"{couch_url}/order_items/_design/order_items/_view/by_order_id",
        json={"keys": order_ids, "include_docs": True},
    )
    order_items_data = order_items_response.json()
    order_items = {}
    for row in order_items_data.get("rows", []):
        order_id = row["key"]
        if order_id not in order_items:
            order_items[order_id] = []
        order_items[order_id].append(row["doc"])

    product_ids = []
    seller_ids = []
    for items_list in order_items.values():
        for item in items_list:
            product_ids.append(item.get("product_id"))
            seller_ids.append(item.get("seller_id"))

    products_response = requests.post(
        f"{couch_url}/products/_design/products/_view/by_id",
        json={"keys": product_ids, "include_docs": True},
    )
    products_data = products_response.json()
    products = {row["key"]: row["doc"] for row in products_data.get("rows", [])}

    sellers_response = requests.post(
        f"{couch_url}/sellers/_design/sellers/_view/by_id",
        json={"keys": seller_ids, "include_docs": True},
    )
    sellers_data = sellers_response.json()
    sellers = {row["key"]: row["doc"] for row in sellers_data.get("rows", [])}

    payments_response = requests.post(
        f"{couch_url}/order_payments/_design/order_payments/_view/by_order_id",
        json={"keys": order_ids, "include_docs": True},
    )
    payments_data = payments_response.json()
    payments = {}
    for row in payments_data.get("rows", []):
        payments[row["key"]] = row["doc"]

    reviews_response = requests.post(
        f"{couch_url}/order_reviews/_design/order_reviews/_view/by_order_id",
        json={"keys": order_ids, "include_docs": True},
    )
    reviews_data = reviews_response.json()
    reviews = {}
    for row in reviews_data.get("rows", []):
        reviews[row["key"]] = row["doc"]

    results = []
    for order in orders:
        order_id = order.get("order_id")
        customer_id = order.get("customer_id")

        for item in order_items.get(order_id, []):
            product_id = item.get("product_id")
            seller_id = item.get("seller_id")

            result = {
                "order_id": order_id,
                "order_status": order.get("order_status"),
                "order_purchase_timestamp": order.get("order_purchase_timestamp"),
                "customer_id": customer_id,
                "customer_city": customers.get(customer_id, {}).get("customer_city"),
                "customer_state": customers.get(customer_id, {}).get("customer_state"),
                "order_item_id": item.get("order_item_id"),
                "price": item.get("price"),
                "freight_value": item.get("freight_value"),
                "product_id": product_id,
                "product_category_name": products.get(product_id, {}).get(
                    "product_category_name"
                ),
                "seller_id": seller_id,
                "seller_city": sellers.get(seller_id, {}).get("seller_city"),
                "seller_state": sellers.get(seller_id, {}).get("seller_state"),
                "payment_type": payments.get(order_id, {}).get("payment_type"),
                "payment_value": payments.get(order_id, {}).get("payment_value"),
                "review_score": reviews.get(order_id, {}).get("review_score"),
            }

            results.append(result)

            if len(results) >= limit:
                break

        if len(results) >= limit:
            break

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
