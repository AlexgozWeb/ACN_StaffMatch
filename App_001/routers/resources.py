import uuid
from fastapi import APIRouter, HTTPException, Depends
from models.schemas import Risorsa, RisorsaCreate
from services import auth_service, db

router = APIRouter(prefix="/resources", tags=["Risorse"])

@router.get("/")
def list_resources(current_user: dict = Depends(auth_service.get_current_user)):
    resources = db.get_resources()
    roles = {r["id"]: r for r in db.get_roles()}
    result = []
    for r in resources:
        if r["id"] == "R000":
            continue
        ruolo = roles.get(r["ruolo_id"], {})
        result.append({
            **r,
            "password_hash": "***",
            "ruolo_nome": ruolo.get("nome", ""),
            "seniority": ruolo.get("seniority", ""),
            "disponibilita_percentuale": db.disponibilita_risorsa(r["id"]),
        })
    return result

@router.get("/{resource_id}")
def get_resource(resource_id: str, current_user: dict = Depends(auth_service.get_current_user)):
    resources = db.get_resources()
    r = next((r for r in resources if r["id"] == resource_id), None)
    if not r:
        raise HTTPException(status_code=404, detail="Risorsa non trovata")
    roles = {r2["id"]: r2 for r2 in db.get_roles()}
    ruolo = roles.get(r["ruolo_id"], {})
    return {
        **r,
        "password_hash": "***",
        "ruolo_nome": ruolo.get("nome", ""),
        "seniority": ruolo.get("seniority", ""),
        "disponibilita_percentuale": db.disponibilita_risorsa(r["id"]),
        "allocazioni": [a for a in db.get_allocations() if a["risorsa_id"] == resource_id],
    }

@router.post("/", status_code=201)
def create_resource(
    body: RisorsaCreate,
    current_user: dict = Depends(auth_service.is_manager_or_admin),
):
    resources = db.get_resources()
    if any(r["email"] == body.email for r in resources):
        raise HTTPException(status_code=400, detail="Email già presente")
    roles = {r["id"]: r for r in db.get_roles()}
    ruolo = roles.get(body.ruolo_id)
    if not ruolo:
        raise HTTPException(status_code=400, detail="Ruolo non valido")
    new_id = f"R{str(uuid.uuid4())[:8].upper()}"
    new_resource = {
        "id": new_id,
        "nome": body.nome,
        "cognome": body.cognome,
        "email": body.email,
        "data_nascita": body.data_nascita,
        "ruolo_id": body.ruolo_id,
        "costo_orario": body.costo_orario if body.costo_orario is not None else ruolo["costo_orario"],
        "skill_ids": [s.model_dump() for s in body.skill_ids],
        "lingue": body.lingue,
        "is_active": True,
        "password_hash": auth_service.hash_password("init01"),
        "gruppo_ruolo_ids": body.gruppo_ruolo_ids,
    }
    resources.append(new_resource)
    db.save_resources(resources)
    return {**new_resource, "password_hash": "***"}
