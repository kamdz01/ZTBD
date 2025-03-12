import asyncio
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

app = FastAPI()

# Konfiguracja CORS
origins = [
    "http://localhost:3000",  # przykładowy adres frontendu
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lub allow_origins=["*"] aby zezwolić na wszystkie źródła (niezalecane w produkcji)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model walidacji danych wejściowych
class ScriptRequest(BaseModel):
    script_name: str

# Asynchroniczna funkcja do strumieniowania wyjścia skryptu w formacie NDJSON
async def stream_script_output_json(script_path: str):
    process = await asyncio.create_subprocess_exec(
        "python", "-u", script_path,  # -u: unbuffered output
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        # Konwertujemy linie na JSON i dodajemy znak nowej linii
        # json_line = json.dumps({"output": line.decode("utf-8").strip()})
        # yield json_line + "\n"
        yield line
    await process.wait()

@app.post("/execute")
async def execute_script(request: ScriptRequest):
    # Mapowanie nazw skryptów na ścieżki do plików
    script_map = {
        "file1": "app/file1.py",
        "file2": "app/file2.py",
        "file3": "app/file3.py"
    }
    script_path = script_map.get(request.script_name)
    if not script_path:
        raise HTTPException(status_code=400, detail="Niepoprawna nazwa skryptu.")
    
    # Zwracamy StreamingResponse z odpowiednim media type dla NDJSON
    return StreamingResponse(stream_script_output_json(script_path), media_type="application/x-ndjson")
