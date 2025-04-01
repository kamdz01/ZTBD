import sys
import json
import time
import requests


def run_join_test():
    # Konfiguracja CouchDB
    couch_url = "http://admin:admin@localhost:5984"

    # Tworzenie widoków, jeśli nie istnieją
    design_doc_orders = {
        "_id": "_design/orders",
        "views": {
            "approved_by_customer": {
                "map": """function(doc) {
                    if (doc.order_status === 'approved') {
                        emit(doc.customer_id, {
                            purchase_date: doc.order_purchase_timestamp
                        });
                    }
                }""",
                "reduce": """function(keys, values, rereduce) {
                    var result = {
                        count: 0,
                        latest_date: ''
                    };
                    
                    for (var i = 0; i < values.length; i++) {
                        if (rereduce) {
                            result.count += values[i].count;
                            result.latest_date = values[i].latest_date > result.latest_date ? values[i].latest_date : result.latest_date;
                        } else {
                            result.count += 1;
                            var date = values[i].purchase_date;
                            result.latest_date = date > result.latest_date ? date : result.latest_date;
                        }
                    }
                    
                    return result;
                }"""
            }
        },
        "language": "javascript"
    }
    
    # Tworzymy widok dla customers, który mapuje customer_id na dane klienta
    design_doc_customers = {
        "_id": "_design/customers",
        "views": {
            "by_customer_id": {
                "map": """function(doc) {
                    if (doc.customer_id) {
                        emit(doc.customer_id, doc);
                    }
                }"""
            }
        },
        "language": "javascript"
    }
    
    # Start pomiaru czasu
    start_time = time.time()
    
    # Utworzenie widoków (pomijamy czas tego etapu)
    try:
        requests.put(f"{couch_url}/orders/_design/orders", json=design_doc_orders)
        requests.put(f"{couch_url}/customers/_design/customers", json=design_doc_customers)
    except Exception as e:
        print(f"Błąd przy tworzeniu widoków: {e}")
    
    # Pobieranie zamówień "approved" pogrupowanych wg klienta z redukcją
    view_url = f"{couch_url}/orders/_design/orders/_view/approved_by_customer"
    params = {
        "group": "true"
    }
    
    response = requests.get(view_url, params=params)
    data = response.json()
    
    # Sprawdzenie czy mamy jakiekolwiek dane z widoku
    print(f"Liczba wszystkich wierszy z widoku: {len(data.get('rows', []))}")
    
    # Filtrujemy klientów z co najmniej 1 zamówieniem (tak jak w SQL HAVING COUNT(*) >= 1)
    filtered_customers = [row for row in data.get("rows", []) if row["value"]["count"] >= 1]
    print(f"Liczba klientów po filtrowaniu: {len(filtered_customers)}")
    
    # Dla przefiltrowanych klientów pobieramy ich dane
    customer_ids = [row["key"] for row in filtered_customers]
    print(f"ID klientów do pobrania: {customer_ids}")
    
    # Pobieranie danych klientów za pomocą widoku by_customer_id
    results = []
    if customer_ids:
        customer_dict = {}
        
        # Pobieranie danych klientów przy użyciu widoku by_customer_id
        for customer_id in customer_ids:
            try:
                customer_view_url = f"{couch_url}/customers/_design/customers/_view/by_customer_id"
                params = {
                    "key": f'"{customer_id}"',  # CouchDB wymaga cudzysłowów dla kluczy będących ciągami znaków
                    "include_docs": "true"
                }
                response = requests.get(customer_view_url, params=params)
                
                if response.status_code == 200:
                    customer_data = response.json()
                    if customer_data.get("rows") and len(customer_data["rows"]) > 0:
                        # Dostęp do dokumentu klienta
                        customer_dict[customer_id] = customer_data["rows"][0]["value"]
                    else:
                        print(f"Nie znaleziono klienta o customer_id: {customer_id}")
                else:
                    print(f"Błąd podczas pobierania klienta {customer_id}, kod: {response.status_code}")
                    print(response.text)
            except Exception as e:
                print(f"Błąd przy pobieraniu klienta {customer_id}: {e}")
        
        print(f"Liczba poprawnych dokumentów klientów: {len(customer_dict)}")
        
        for customer_info in filtered_customers:
            customer_id = customer_info["key"]
            if customer_id in customer_dict:
                customer = customer_dict[customer_id]
                results.append({
                    "customer_id": customer_id,
                    "customer_city": customer.get("customer_city", ""),
                    "total_orders": customer_info["value"]["count"],
                    "last_order_purchase_timestamp": customer_info["value"]["latest_date"]
                })
            else:
                print(f"Nie znaleziono klienta o ID: {customer_id}")
    
    # Sortowanie wyników wg daty ostatniego zamówienia
    results.sort(key=lambda x: x["last_order_purchase_timestamp"], reverse=True)
    print(f"Końcowa liczba wyników: {len(results)}")
    
    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Zwracanie wyniku
    result = {"time": elapsed_time, "rows": len(results)}
    print(json.dumps(result))
    
    return elapsed_time, results


if __name__ == "__main__":
    run_join_test()