import uuid
from fastapi import APIRouter, HTTPException, Depends
from models.schemas import ProgettoCreate
from services import auth_service, db

router = APIRouter(prefix="/projects", tags=["Progetti"])

@router.get("/")
def list_projects(current_user: dict = Depends(auth_service.get_current_user)):
    projects = db.get_projects()
    skills = {s["id"]: s for s in db.get_skills()}
    result = []
    for p in projects:
        skill_nome = skills.get(p["skill_principale_id"], {}).get("nome", "")
        allocazioni = [a for a in db.get_allocations() if a["progetto_id"] == p["id"]]
        result.append({**p, "skill_principale_nome": skill_nome, "num_risorse": len(allocazioni)})
    return result

@router.get("/{project_id}")
def get_project(project_id: str, current_user: dict = Depends(auth_service.get_current_user)):
    projects = db.get_projects()
    p = next((p for p in projects if p["id"] == project_id), None)
    if not p:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    allocazioni = [a for a in db.get_allocations() if a["progetto_id"] == project_id]
    return {**p, "allocazioni": allocazioni}

@router.post("/", status_code=201)
def create_project(
    body: ProgettoCreate,
    current_user: dict = Depends(auth_service.is_manager_or_admin),
):
    new_id = f"P{str(uuid.uuid4())[:8].upper()}"
    new_project = {
        "id": new_id,
        **body.model_dump(),
        "referente_it_cliente": body.referente_it_cliente.model_dump(),
        "stato": "Active",
    }
    projects = db.get_projects()
    projects.append(new_project)
    db.save_projects(projects)
    return new_project
