import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def _load(filename: str) -> list:
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)

def _save(filename: str, data: list):
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_skills():       return _load("skills.json")
def get_roles():        return _load("roles.json")
def get_role_groups():  return _load("role_groups.json")
def get_resources():    return _load("resources.json")
def get_projects():     return _load("projects.json")
def get_allocations():  return _load("allocations.json")
def get_opportunities():return _load("opportunities.json")
def get_match_results():return _load("match_results.json")

def save_resources(data):     _save("resources.json", data)
def save_projects(data):      _save("projects.json", data)
def save_opportunities(data): _save("opportunities.json", data)
def save_match_results(data): _save("match_results.json", data)
def save_role_groups(data):   _save("role_groups.json", data)

def disponibilita_risorsa(risorsa_id: str) -> int:
    allocazioni = [a for a in get_allocations() if a["risorsa_id"] == risorsa_id]
    totale = sum(a["percentuale"] for a in allocazioni)
    return max(0, 100 - totale)
