import requests
import json
import os
import pprint
from dotenv import load_dotenv
from pathlib import Path

# получаем ключи через os.getenv
env_path = Path.cwd() / '.env' 
load_dotenv(env_path)

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

IMPLEMENTATION = "0xE66f6a37C807F71591854e22075b3A613B46abe2" # адрес волта с кодом (не прокси)

url = "https://api.etherscan.io/v2/api"

params = {
    "chainid": 1,                     
    "module": "contract",
    "action": "getsourcecode",
    "address": IMPLEMENTATION,
    "apikey": ETHERSCAN_API_KEY
}

response = requests.get(url, params=params).json()
result = response["result"][0]

pprint.pprint(response)

# ABI
with open("abi.json", "w") as f:
    json.dump(json.loads(result["ABI"]), f, indent=2)

# Исходный код
source = result["SourceCode"]

os.makedirs("contracts", exist_ok=True)

# Если контракт состоит из нескольких файлов
if source.startswith("{"):
    sources = json.loads(source[1:-1])["sources"]
    for path, data in sources.items():
        filename = path.replace("/", "_")
        with open(f"contracts/{filename}", "w") as f:
            f.write(data["content"])
else:
    # Один файл
    with open("contracts/Contract.sol", "w") as f:
        f.write(source)

print("Код и ABI скачаны")
