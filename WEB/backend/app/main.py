import asyncio
import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lub allow_origins=["*"] aby zezwolić na wszystkie źródła (niezalecane w produkcji)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/insertTest")
async def read_root():
    return {"message": "Hello World"}

@app.get("/inserttest")
async def read_root():
    return {"message": "Hello"}


# Funkcja pomocnicza, która wykonuje test i aktualizuje plik wyników
async def process_test(database: str, scenario: str, size: int = None) -> dict:
    # Wczytujemy dane z tests.json
    tests_file = os.path.join(os.path.dirname(__file__), "tests", "tests.json")
    with open(tests_file, "r") as f:
        tests = json.load(f)
    
    # Walidacja bazy danych i scenariusza
    if database not in tests["databases"]:
        raise HTTPException(status_code=400, detail="Niepoprawna baza danych.")
    if scenario not in tests["testScenarios"]:
        raise HTTPException(status_code=400, detail="Niepoprawny scenariusz testowy.")
    
    scenario_data = tests["testScenarios"][scenario]
    # Jeśli scenariusz wymaga rozmiaru, size musi być podany i poprawny
    if "sizes" in scenario_data:
        if size is None:
            raise HTTPException(status_code=400, detail="Ten scenariusz wymaga podania parametru 'size'.")
        if size not in scenario_data["sizes"]:
            raise HTTPException(status_code=400, detail="Niepoprawny rozmiar testu.")
    else:
        if size is not None:
            raise HTTPException(status_code=400, detail="Ten scenariusz testowy nie przyjmuje parametru 'size'.")
    
    db_folder = database.lower()
    if not db_folder:
        raise HTTPException(status_code=400, detail="Brak katalogu dla danej bazy danych.")
    
    # Budujemy ścieżkę do skryptu, np. "tests/mongodb/insertTest.py" lub "tests/mongodb/fillTest.py"
    script_file = os.path.join(os.path.dirname(__file__), "tests", db_folder, f"{scenario}.py")
    print("Script path:", script_file)
    if not os.path.exists(script_file):
        raise HTTPException(status_code=400, detail="Brak skryptu dla danego scenariusza.")
    
    # Budujemy argumenty wywołania – dodajemy parametr size, jeśli istnieje
    cmd = ["python", "-u", script_file]
    if size is not None:
        cmd.append(str(size))
    print("CMD:", cmd)
    
    # Uruchamiamy proces i parsujemy wynik (oczekujemy JSON z kluczem "time")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    output_time = 0
    while True:
        line = await process.stdout.readline()
        print("LINE:", line)
        if not line:
            break
        try:
            data = json.loads(line.decode("utf-8").strip())
            if "time" in data:
                output_time = data["time"]
        except Exception:
            print("ERR przy parsowaniu linii")
            continue
    await process.wait()
    
    print("Output times:", output_time)
    
    # Aktualizacja pliku testResults.json
    results_file = os.path.join(os.path.dirname(__file__), "tests", "testResults.json")
    with open(results_file, "r") as f:
        results = json.load(f)
    
    if database not in results:
        results[database] = {}
    if scenario not in results[database]:
        results[database][scenario] = {}
    
    # Używamy klucza "default" dla testów bez parametru size
    key = str(size) if size is not None else "default"
    if key not in results[database][scenario]:
        results[database][scenario][key] = {"times": []}
    
    results[database][scenario][key]["times"].append(output_time)
    
    with open(results_file, "w") as f:
        json.dump(results, f, indent=4)
    
    # Odczytujemy zaktualizowane wyniki i zwracamy je
    with open(results_file, "r") as f:
        updated_results = json.load(f)
    final_output_times = updated_results[database][scenario][key]["times"]
    return {"result": output_time}
    return {"database": database, "scenario": scenario, "size": size, "times": final_output_times}

# Endpoint dla scenariuszy, które wymagają parametru size (np. /mongodb/insertTest/10)
@app.get("/run/{database}/{scenario}/{size}")
async def run_test_with_size(database: str, scenario: str, size: int):
    return await process_test(database, scenario, size)

# Endpoint dla scenariuszy, które nie przyjmują parametru size (np. /mongodb/fillTest)
@app.get("/run/{database}/{scenario}")
async def run_test_without_size(database: str, scenario: str):
    return await process_test(database, scenario)

@app.get("/databases")
async def get_databases():
    tests_file = os.path.join(os.path.dirname(__file__), "tests", "tests.json")
    with open(tests_file, "r") as f:
        tests = json.load(f)
    return {"databases": tests.get("databases", [])}

@app.get("/test-scenarios")
async def get_test_scenarios():
    tests_file = os.path.join(os.path.dirname(__file__), "tests", "tests.json")
    with open(tests_file, "r") as f:
        tests = json.load(f)
    return {"testScenarios": tests.get("testScenarios", {})}

@app.get("/results/{database}/{scenario}/{size}")
async def get_results(database: str, scenario: str, size: str):
    results_file = os.path.join(os.path.dirname(__file__), "tests", "testResults.json")
    with open(results_file, "r") as f:
        results = json.load(f)
    
    key = str(size)  # dla testów bez parametru size używamy "default", tutaj size to liczba
    try:
        times = results[database][scenario][key]["times"]
    except KeyError:
        raise HTTPException(status_code=404, detail="Wyniki nie znalezione dla podanych parametrów")
    
    return {"database": database, "scenario": scenario, "size": size, "times": times}