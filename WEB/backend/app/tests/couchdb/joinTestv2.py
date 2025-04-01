import sys
import json
import time
import requests


def run_join_test(limit=10):
    """
    Wykonuje złożone zapytanie z wieloma relacjami i zwraca w JSON
    czas wykonania zapytania.
    """
    # Konfiguracja CouchDB
    couch_url = "http://admin:admin@localhost:5984"
    
    # Rozpoczęcie pomiaru czasu
    start_time = time.time()
    
    # 1. Pobieramy zamówienia ze statusem 'delivered'
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
    
    if not orders:
        end_time = time.time()
        result = {"time": end_time - start_time}
        print(json.dumps(result))
        return end_time - start_time
    
    # Pobieranie identyfikatorów dla dalszych zapytań
    order_ids = [order["_id"] for order in orders]
    customer_ids = [order.get("customer_id") for order in orders]
    
    # 2. Pobieranie danych klientów
    customers_response = requests.post(
        f"{couch_url}/customers/_all_docs",
        json={"keys": customer_ids, "include_docs": True},
    )
    customers_data = customers_response.json()
    customers = {row["key"]: row["doc"] for row in customers_data.get("rows", []) if "doc" in row}
    
    # 3. Pobieranie elementów zamówień
    order_items_view_url = f"{couch_url}/order_items/_design/order_items/_view/by_order_id"
    order_items_response = requests.post(
        order_items_view_url,
        json={"keys": order_ids, "include_docs": True},
    )
    order_items_data = order_items_response.json()
    
    # Grupowanie elementów zamówień wg order_id
    order_items = {}
    product_ids = []
    seller_ids = []
    
    for row in order_items_data.get("rows", []):
        order_id = row["key"]
        if "doc" in row:
            if order_id not in order_items:
                order_items[order_id] = []
            order_items[order_id].append(row["doc"])
            
            if "product_id" in row["doc"]:
                product_ids.append(row["doc"]["product_id"])
            if "seller_id" in row["doc"]:
                seller_ids.append(row["doc"]["seller_id"])
    
    # 4. Pobieranie danych produktów
    products_response = requests.post(
        f"{couch_url}/products/_all_docs",
        json={"keys": product_ids, "include_docs": True},
    )
    products_data = products_response.json()
    products = {row["key"]: row["doc"] for row in products_data.get("rows", []) if "doc" in row}
    
    # Pobieramy kategorie produktów dla tłumaczeń
    category_names = [product.get("product_category_name") for product in products.values() 
                     if product.get("product_category_name")]
    
    # 5. Pobieranie tłumaczeń kategorii
    translations_response = requests.post(
        f"{couch_url}/product_category_name_translation/_all_docs",
        json={"keys": category_names, "include_docs": True},
    )
    translations_data = translations_response.json()
    translations = {row["key"]: row["doc"] for row in translations_data.get("rows", []) if "doc" in row}
    
    # 6. Pobieranie danych sprzedawców
    sellers_response = requests.post(
        f"{couch_url}/sellers/_all_docs",
        json={"keys": seller_ids, "include_docs": True},
    )
    sellers_data = sellers_response.json()
    sellers = {row["key"]: row["doc"] for row in sellers_data.get("rows", []) if "doc" in row}
    
    # 7. Pobieranie recenzji
    reviews_response = requests.post(
        f"{couch_url}/order_reviews/_all_docs",
        json={"keys": order_ids, "include_docs": True},
    )
    reviews_data = reviews_response.json()
    reviews = {row["key"]: row["doc"] for row in reviews_data.get("rows", []) if "doc" in row}
    
    # Tworzenie wynikowego zbioru danych
    results = []
    
    for order in orders:
        order_id = order["_id"]
        order_items_list = order_items.get(order_id, [])
        
        for item in order_items_list:
            product_id = item.get("product_id")
            seller_id = item.get("seller_id")
            
            product_category = products.get(product_id, {}).get("product_category_name", "")
            
            result = {
                "order_id": order_id,
                "customer_city": customers.get(order.get("customer_id"), {}).get("customer_city", ""),
                "customer_state": customers.get(order.get("customer_id"), {}).get("customer_state", ""),
                "seller_city": sellers.get(seller_id, {}).get("seller_city", ""),
                "seller_state": sellers.get(seller_id, {}).get("seller_state", ""),
                "product_category_name": product_category,
                "product_category_name_english": translations.get(product_category, {}).get("product_category_name_english", ""),
                "review_score": reviews.get(order_id, {}).get("review_score", None)
            }
            
            results.append(result)
            
            # Ograniczamy wyniki do limitu
            if len(results) >= limit:
                break
        
        if len(results) >= limit:
            break
    
    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Zwracanie wyniku
    result = {"time": elapsed_time}
    print(json.dumps(result))
    
    return elapsed_time


if __name__ == "__main__":
    # Domyślnie pobieramy 10 rekordów, chyba że podano inny limit w argumentach
    limit = 10
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
        
    run_join_test(limit)