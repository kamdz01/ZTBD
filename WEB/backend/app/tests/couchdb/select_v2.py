import sys
import json
import time
import requests


def run_select_test(limit=100):
    # Konfiguracja CouchDB
    couch_url = "http://admin:admin@localhost:5984"

    # Start pomiaru czasu
    start_time = time.time()

    # Definicja dokumentu design z widokiem map-reduce
    design_doc = {
        "_id": "_design/orders",
        "views": {
            "daily_orders": {
                "map": "function(doc) { "
                "  if (doc.order_purchase_timestamp) { "
                "    emit(doc.order_purchase_timestamp.substring(0, 10), 1); "
                "  } "
                "}",
                "reduce": "_count",
            }
        },
        "language": "javascript",
    }

    # Próba utworzenia lub aktualizacji dokumentu design
    try:
        # PUT do dokumentu design - jeśli dokument już istnieje, zostanie nadpisany
        requests.put(f"{couch_url}/orders/_design/orders", json=design_doc)
    except Exception as e:
        # Ignorujemy błędy, dokument może już istnieć
        print(f"Błąd podczas tworzenia dokumentu design: {e}")

    # Zapytanie do widoku z parametrem group=true (grupowanie wg klucza)
    view_url = f"{couch_url}/orders/_design/orders/_view/daily_orders"
    params = {"group": "true", "limit": limit}

    response = requests.get(view_url, params=params)
    data = response.json()

    # Przetwarzanie wyników widoku
    results = []
    for row in data.get("rows", []):
        results.append({"day": row["key"], "order_count": row["value"]})

    # Koniec pomiaru czasu
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Zwracanie wyniku testu
    result = {"time": elapsed_time, "count": len(results)}
    print(json.dumps(result, indent=2))

    return elapsed_time


if __name__ == "__main__":
    # Pobranie limitu z argumentów (domyślnie 100)
    limit = 100
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    run_select_test(limit)
