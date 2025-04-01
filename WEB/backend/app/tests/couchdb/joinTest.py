import json
import time
import requests

def run_join_test():
    # Konfiguracja CouchDB
    couch_url = "http://admin:admin@localhost:5984"
    orders_db = f"{couch_url}/orders"
    customers_db = f"{couch_url}/customers"
    
    start_time = time.time()
    
    # Zapytanie do bazy "orders": wybieramy zamówienia o statusie 'approved'
    orders_query_url = f"{orders_db}/_find"
    orders_query = {
        "selector": {"order_status": "approved"},
        "fields": ["customer_id", "order_purchase_timestamp"]
    }
    
    response = requests.post(orders_query_url, json=orders_query)
    if response.status_code != 200:
        print("Błąd pobierania zamówień:", response.text)
        return
    
    orders_data = response.json().get("docs", [])
    
    # Grupowanie zamówień według customer_id oraz agregacja danych:
    # - total_orders: liczba zamówień
    # - last_order_purchase_timestamp: data ostatniego zamówienia
    customer_orders = {}
    for order in orders_data:
        cust_id = order.get("customer_id")
        if cust_id is None:
            continue
        ts = order.get("order_purchase_timestamp")
        if cust_id not in customer_orders:
            customer_orders[cust_id] = {"total_orders": 0, "last_order_purchase_timestamp": ts}
        customer_orders[cust_id]["total_orders"] += 1
        if ts > customer_orders[cust_id]["last_order_purchase_timestamp"]:
            customer_orders[cust_id]["last_order_purchase_timestamp"] = ts
            
    # Filtracja klientów posiadających co najmniej 2 zatwierdzone zamówienia
    filtered_customers = {cid: data for cid, data in customer_orders.items() if data["total_orders"] >= 2}
    
    # Pobieranie danych klientów z bazy "customers" i łączenie z danymi zagregowanymi
    join_results = []
    for cust_id, agg in filtered_customers.items():
        customer_url = f"{customers_db}/{cust_id}"
        cust_response = requests.get(customer_url)
        if cust_response.status_code != 200:
            continue
        cust_data = cust_response.json()
        join_results.append({
            "customer_id": cust_id,
            "customer_city": cust_data.get("customer_city"),
            "total_orders": agg["total_orders"],
            "last_order_purchase_timestamp": agg["last_order_purchase_timestamp"]
        })
    
    # Sortowanie wyników malejąco wg daty ostatniego zamówienia
    join_results.sort(key=lambda x: x["last_order_purchase_timestamp"], reverse=True)
    row_count = len(join_results)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    result = {"time": elapsed_time, "rows": row_count}
    print(json.dumps(result))
    
    return elapsed_time, join_results

if __name__ == "__main__":
    run_join_test()