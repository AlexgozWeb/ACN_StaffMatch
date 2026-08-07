import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any
from services import auth_service, db

router = APIRouter(prefix="/project-changes", tags=["Modifiche Progetto"])


class ProposeChangeRequest(BaseModel):
    change_type: str          # "update_info" | "add_resource" | "remove_resource"
    payload: dict[str, Any]
    note_manager: str = ""


def _check_owner(project: dict, current_user: dict):
    groups = current_user.get("gruppi", [])
    is_admin = "Administrator" in groups
    is_owner = project.get("manager_id") == current_user["id"]
    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Puoi modificare solo i tuoi progetti")


@router.post("/propose/{project_id}", status_code=201)
def propose_change(
    project_id: str,
    body: ProposeChangeRequest,
    current_user: dict = Depends(auth_service.is_manager_or_admin),
):
    projects = db.get_projects()
    p = next((p for p in projects if p["id"] == project_id), None)
    if not p:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    _check_owner(p, current_user)
    if p.get("stato") != "Active":
        raise HTTPException(status_code=400, detail="Solo i progetti Attivi possono essere modificati")

    valid_types = ("update_info", "add_resource", "remove_resource")
    if body.change_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"change_type deve essere uno di {valid_types}")

    if body.change_type == "remove_resource":
        allocation_id = body.payload.get("allocation_id")
        if not allocation_id:
            raise HTTPException(status_code=400, detail="allocation_id richiesto per remove_resource")
        alloc = next((a for a in db.get_allocations()
                      if a["id"] == allocation_id and a["progetto_id"] == project_id), None)
        if not alloc:
            raise HTTPException(status_code=404, detail="Allocazione non trovata")

    if body.change_type == "add_resource":
        risorsa_id = body.payload.get("risorsa_id")
        if not any(r["id"] == risorsa_id for r in db.get_resources()):
            raise HTTPException(status_code=404, detail="Risorsa non trovata")
        existing = [a for a in db.get_allocations()
                    if a["progetto_id"] == project_id and a["risorsa_id"] == risorsa_id]
        if existing:
            raise HTTPException(status_code=400, detail="Risorsa già allocata su questo progetto")

    new_req = {
        "id": f"PCR{str(uuid.uuid4())[:8].upper()}",
        "project_id": project_id,
        "project_nome": p.get("nome", ""),
        "project_cliente": p.get("cliente", ""),
        "requested_by_id": current_user["id"],
        "requested_by_nome": f"{current_user['nome']} {current_user['cognome']}",
        "requested_at": datetime.utcnow().isoformat(),
        "stato": "Pending",
        "change_type": body.change_type,
        "payload": body.payload,
        "note_manager": body.note_manager,
        "note_executive": None,
        "reviewed_by_id": None,
        "reviewed_at": None,
    }
    reqs = db.get_project_change_requests()
    reqs.append(new_req)
    db.save_project_change_requests(reqs)
    return new_req


@router.get("/pending")
def get_pending(current_user: dict = Depends(auth_service.is_executive_or_admin)):
    reqs = db.get_project_change_requests()
    pending = [r for r in reqs if r["stato"] == "Pending"]
    resources = {r["id"]: r for r in db.get_resources()}
    allocations = {a["id"]: a for a in db.get_allocations()}
    result = []
    for req in pending:
        enriched = dict(req)
        pl = req.get("payload", {})
        if req["change_type"] == "add_resource":
            rid = pl.get("risorsa_id", "")
            r = resources.get(rid, {})
            enriched["risorsa_nome"] = f"{r.get('nome','')} {r.get('cognome','')}"
        elif req["change_type"] == "remove_resource":
            aid = pl.get("allocation_id", "")
            alloc = allocations.get(aid, {})
            rid = alloc.get("risorsa_id", "")
            r = resources.get(rid, {})
            enriched["risorsa_nome"] = f"{r.get('nome','')} {r.get('cognome','')}"
            enriched["allocazione"] = alloc
        result.append(enriched)
    return result


@router.get("/")
def get_all(current_user: dict = Depends(auth_service.get_current_user)):
    return db.get_project_change_requests()


@router.patch("/{request_id}/review")
def review_change(
    request_id: str,
    decision: str,
    note_executive: str = "",
    current_user: dict = Depends(auth_service.is_executive_or_admin),
):
    if decision not in ("Approved", "Rejected"):
        raise HTTPException(status_code=400, detail="decision deve essere 'Approved' o 'Rejected'")

    reqs = db.get_project_change_requests()
    req = next((r for r in reqs if r["id"] == request_id), None)
    if not req:
        raise HTTPException(status_code=404, detail="Richiesta non trovata")
    if req["stato"] != "Pending":
        raise HTTPException(status_code=400, detail="Richiesta già elaborata")

    req["stato"] = decision
    req["note_executive"] = note_executive
    req["reviewed_by_id"] = current_user["id"]
    req["reviewed_at"] = datetime.utcnow().isoformat()
    db.save_project_change_requests(reqs)

    if decision == "Approved":
        change_type = req["change_type"]
        payload = req["payload"]
        project_id = req["project_id"]

        if change_type == "update_info":
            projects = db.get_projects()
            for p in projects:
                if p["id"] == project_id:
                    allowed = ("nome", "cliente", "data_fine_prevista", "descrizione")
                    for k, v in payload.items():
                        if k in allowed:
                            p[k] = v
                    break
            db.save_projects(projects)
            return {"message": "Modifiche progetto applicate"}

        elif change_type == "add_resource":
            allocs = db.get_allocations()
            allocs.append({
                "id": f"ALL{str(uuid.uuid4())[:8].upper()}",
                "risorsa_id": payload["risorsa_id"],
                "progetto_id": project_id,
                "percentuale": payload.get("percentuale", 50),
                "data_inizio": payload.get("data_inizio", ""),
                "data_fine": payload.get("data_fine", ""),
                "ruolo_nel_progetto": payload.get("ruolo_nel_progetto", "Consultant"),
            })
            db.save_allocations(allocs)
            return {"message": "Risorsa aggiunta al progetto"}

        elif change_type == "remove_resource":
            allocs = db.get_allocations()
            db.save_allocations([a for a in allocs if a["id"] != payload["allocation_id"]])
            return {"message": "Risorsa rilasciata dal progetto"}

    return {"message": f"Richiesta {decision}"}
