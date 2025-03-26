import sys
import json
import time
import random
import string
import sqlite3
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

    return (
        generate_id(),
        generate_id(),
        random.randint(10000, 99999),
        random.choice(cities),
        random.choice(states),
    )


def generate_order_data(customer_id):
    order_statuses = ["delivered", "shipped", "processing", "canceled", "approved"]

    return (
        generate_id(),
        customer_id,
        random.choice(order_statuses),
        generate_date(),
        generate_date(),
        generate_date(),
        generate_date(),
        generate_date(),
    )


def run_insert_test(size):

    conn = sqlite3.connect(
        "/Users/mptb/Documents/Studia/Data_Science/1_sem/ZTBD/ZTBD/DB/SQLite/olist.sqlite"
    )
    cursor = conn.cursor()

    start_time = time.time()

    customers_ids = []

    cursor.execute("BEGIN TRANSACTION")
    for _ in range(size):
        customer = generate_customer_data()
        cursor.execute(
            """
            INSERT INTO customers (customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state)
            VALUES (?, ?, ?, ?, ?)
        """,
            customer,
        )
        customers_ids.append(customer[0])

    for customer_id in customers_ids:
        num_orders = random.randint(1, 3)
        for _ in range(num_orders):
            order = generate_order_data(customer_id)
            cursor.execute(
                """
                INSERT INTO orders (
                    order_id, customer_id, order_status, order_purchase_timestamp, 
                    order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, 
                    order_estimated_delivery_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                order,
            )

    conn.commit()

    end_time = time.time()
    elapsed_time = end_time - start_time

    conn.close()

    result = {"time": elapsed_time}
    print(json.dumps(result))

    return elapsed_time


if __name__ == "__main__":
    size = 10
    if len(sys.argv) > 1:
        size = int(sys.argv[1])

    run_insert_test(size)
