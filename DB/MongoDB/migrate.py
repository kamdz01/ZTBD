import os
import csv
from pymongo import MongoClient

# Konfiguracja połączenia – dostosuj DATABASE_URL oraz nazwę bazy danych według potrzeb
DATABASE_URL = "mongodb://admin:secret@localhost:27017/ecommerce?authSource=admin&directConnection=true"
client = MongoClient(DATABASE_URL)
db = client["ecommerce"]

# Ścieżka do folderu z plikami CSV
csv_folder = "../csv_exports"

def process_csv_file(file_path, collection_name):
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        data = list(reader)
        if data:
            result = db[collection_name].insert_many(data)
            print(f"Wstawiono {len(result.inserted_ids)} rekordów do kolekcji {collection_name}.")

def main():
    # Iteracja po plikach CSV w katalogu csv_exports
    for filename in os.listdir(csv_folder):
        if filename.endswith(".csv"):
            file_path = os.path.join(csv_folder, filename)
            # Używamy nazwy pliku (bez rozszerzenia) jako nazwy kolekcji
            collection_name = os.path.splitext(filename)[0]
            print(f"Przetwarzam plik: {filename} do kolekcji: {collection_name}")
            process_csv_file(file_path, collection_name)

if __name__ == '__main__':
    main()
