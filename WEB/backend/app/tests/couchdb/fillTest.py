import sys
import json
import time
import random
import string
import requests
from datetime import datetime, timedelta


def generate_id(length=20):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def generate_date(start_date=datetime(2018, 1, 1), end_date=datetime(2023, 12, 31)):
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return (start_date + timedelta(days=random_days)).strftime("%Y-%m-%d %H:%M:%S")


def generate_customer_data():
    states = ["SP", "RJ", "MG", "RS", "PR", "SC", "BA", "PE", "CE", "PA"]
    cities = [
        "Sao Paulo",
        "Rio de Janeiro",
        "Belo Horizonte",
        "Porto Alegre",
        "Curitiba",
        "Florianopolis",
        "Salvador",
        "Recife",
        "Fortaleza",
        "Belem",
    ]

    return {
        "_id": generate_id(),
        "customer_unique_id": generate_id(),
        "customer_zip_code_prefix": random.randint(10000, 99999),
        "customer_city": random.choice(cities),
        "customer_state": random.choice(states),
    }


def generate_order_data(customer_id):
    order_statuses = ["delivered", "shipped", "processing", "canceled", "approved"]

    purchase_date = generate_date()

    return {
        "_id": generate_id(),
        "customer_id": customer_id,
        "order_status": random.choice(order_statuses),
        "order_purchase_timestamp": purchase_date,
        "order_approved_at": generate_date(),
        "order_delivered_carrier_date": generate_date(),
        "order_delivered_customer_date": generate_date(),
        "order_estimated_delivery_date": generate_date(),
    }


def run_insert_test(size):

    couch_url = "http://admin:admin@localhost:5984"

    customers_db = "customers"
    orders_db = "orders"

    start_time = time.time()

    customers_ids = []

    customers_to_insert = []
    for _ in range(size):
        customer = generate_customer_data()
        customers_to_insert.append(customer)
        customers_ids.append(customer["_id"])

    if customers_to_insert:
        requests.post(
            f"{couch_url}/{customers_db}/_bulk_docs", json={"docs": customers_to_insert}
        )

    orders_to_insert = []
    for customer_id in customers_ids:
        num_orders = random.randint(1, 3)
        for _ in range(num_orders):
            order = generate_order_data(customer_id)
            orders_to_insert.append(order)

    if orders_to_insert:
        requests.post(
            f"{couch_url}/{orders_db}/_bulk_docs", json={"docs": orders_to_insert}
        )

    end_time = time.time()
    elapsed_time = end_time - start_time

    result = {"time": elapsed_time}
    print(json.dumps(result))

    return elapsed_time


if __name__ == "__main__":

    size = 10
    if len(sys.argv) > 1:
        size = int(sys.argv[1])

    run_insert_test(size)
