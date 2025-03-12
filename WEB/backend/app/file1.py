import time
import json

for i in range(1, 5):
    json_line = json.dumps({f"test-{i}": i*10})
    print(json_line)
    # print(f"Aktualizacja {i}: Praca skryptu...")
    time.sleep(2)  # symulacja długotrwałego działania, 10 sekund przerwy
