import os
import csv
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
print(SCRIPT_DIR)
DATA_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "./..", "csv_exports"))
COUCH_URL = "http://admin:admin@localhost:5984"
CHUNK_SIZE = 10000


def import_csv_to_couchdb(file_path, db_name):
    requests.delete(f"{COUCH_URL}/{db_name}")
    requests.put(f"{COUCH_URL}/{db_name}")

    docs_buffer = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            docs_buffer.append(row)
            if len(docs_buffer) >= CHUNK_SIZE:
                bulk_insert(docs_buffer, db_name)
                docs_buffer = []

        if docs_buffer:
            bulk_insert(docs_buffer, db_name)


def bulk_insert(docs, db_name):
    response = requests.post(f"{COUCH_URL}/{db_name}/_bulk_docs", json={"docs": docs})
    print(f"Inserted {len(docs)} docs into {db_name}: {response.status_code}")


if __name__ == "__main__":
    for file_name in os.listdir(DATA_DIR):
        if file_name.endswith(".csv"):
            db_name = file_name.rsplit(".", 1)[0]
            file_path = os.path.join(DATA_DIR, file_name)
            print(f"Import: {file_path}")
            import_csv_to_couchdb(file_path, db_name)
