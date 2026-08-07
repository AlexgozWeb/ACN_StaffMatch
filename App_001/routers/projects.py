import uuid
from fastapi import APIRouter, HTTPException, Depends
from models.schemas import ProgettoCreate, ProgettoUpdate, AllocazioneCreate
from services import auth_service, db

def _check_owner(project: dict, current_user: dict):
    groups = current_user.get("gruppi", [])
    is_admin = "Administrator" in groups
    is_owner = project.get("manager_id") == current_user["id"]
    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Puoi modificare solo i tuoi progetti")

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


@router.patch("/{project_id}")
def update_project(
    project_id: str,
    body: ProgettoUpdate,
    current_user: dict = Depends(auth_service.is_manager_or_admin),
):
    projects = db.get_projects()
    p = next((p for p in projects if p["id"] == project_id), None)
    if not p:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    _check_owner(p, current_user)
    p.update(body.model_dump(exclude_none=True))
    db.save_projects(projects)
    return p


@router.post("/{project_id}/allocations", status_code=201)
def add_allocation(
    project_id: str,
    body: AllocazioneCreate,
    current_user: dict = Depends(auth_service.is_manager_or_admin),
):
    projects = db.get_projects()
    p = next((p for p in projects if p["id"] == project_id), None)
    if not p:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    _check_owner(p, current_user)

    resources = db.get_resources()
    if not any(r["id"] == body.risorsa_id for r in resources):
        raise HTTPException(status_code=404, detail="Risorsa non trovata")

    existing = [a for a in db.get_allocations()
                if a["progetto_id"] == project_id and a["risorsa_id"] == body.risorsa_id]
    if existing:
        raise HTTPException(status_code=400, detail="Risorsa già allocata su questo progetto")

    new_alloc = {
        "id": f"ALL{str(uuid.uuid4())[:8].upper()}",
        "risorsa_id": body.risorsa_id,
        "progetto_id": project_id,
        "percentuale": body.percentuale,
        "data_inizio": body.data_inizio,
        "data_fine": body.data_fine,
        "ruolo_nel_progetto": body.ruolo_nel_progetto,
    }
    allocations = db.get_allocations()
    allocations.append(new_alloc)
    db.save_allocations(allocations)
    return new_alloc


@router.delete("/{project_id}/allocations/{allocation_id}", status_code=204)
def remove_allocation(
    project_id: str,
    allocation_id: str,
    current_user: dict = Depends(auth_service.is_manager_or_admin),
):
    projects = db.get_projects()
    p = next((p for p in projects if p["id"] == project_id), None)
    if not p:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    _check_owner(p, current_user)

    allocations = db.get_allocations()
    alloc = next((a for a in allocations
                  if a["id"] == allocation_id and a["progetto_id"] == project_id), None)
    if not alloc:
        raise HTTPException(status_code=404, detail="Allocazione non trovata")

    db.save_allocations([a for a in allocations if a["id"] != allocation_id])
