import uuid
from fastapi import APIRouter, HTTPException, Depends
from models.schemas import OpportunityCreate, OpportunityUpdate
from services import auth_service, db

def _check_owner(opp: dict, current_user: dict):
    groups = current_user.get("gruppi", [])
    is_admin = "Administrator" in groups
    is_owner = opp.get("manager_id") == current_user["id"]
    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Puoi modificare solo le tue opportunity")

router = APIRouter(prefix="/opportunities", tags=["Opportunità"])

@router.get("/")
def list_opportunities(current_user: dict = Depends(auth_service.get_current_user)):
    return db.get_opportunities()

@router.get("/{opp_id}")
def get_opportunity(opp_id: str, current_user: dict = Depends(auth_service.get_current_user)):
    opp = next((o for o in db.get_opportunities() if o["id"] == opp_id), None)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunità non trovata")
    results = [m for m in db.get_match_results() if m["opportunity_id"] == opp_id]
    return {**opp, "match_results": results}

@router.post("/", status_code=201)
def create_opportunity(
    body: OpportunityCreate,
    current_user: dict = Depends(auth_service.is_manager_or_admin),
):
    new_id = f"OPP{str(uuid.uuid4())[:8].upper()}"
    new_opp = {
        "id": new_id,
        **body.model_dump(),
        "referente_it_cliente": body.referente_it_cliente.model_dump(),
        "skill_richieste": [s.model_dump() for s in body.skill_richieste],
        "slot_risorse": [s.model_dump() for s in body.slot_risorse],
        "stato": "New",
    }
    opportunities = db.get_opportunities()
    opportunities.append(new_opp)
    db.save_opportunities(opportunities)
    return new_opp


@router.patch("/{opp_id}")
def update_opportunity(
    opp_id: str,
    body: OpportunityUpdate,
    current_user: dict = Depends(auth_service.is_manager_or_admin),
):
    opportunities = db.get_opportunities()
    opp = next((o for o in opportunities if o["id"] == opp_id), None)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity non trovata")
    _check_owner(opp, current_user)
    if opp.get("stato") not in ("New", "Active"):
        raise HTTPException(status_code=400, detail="Non modificabile in questo stato")

    update = body.model_dump(exclude_none=True)
    if "skill_richieste" in update:
        update["skill_richieste"] = [s.model_dump() if hasattr(s, "model_dump") else s
                                     for s in body.skill_richieste]
    if "slot_risorse" in update:
        update["slot_risorse"] = [s.model_dump() if hasattr(s, "model_dump") else s
                                  for s in body.slot_risorse]
    opp.update(update)
    db.save_opportunities(opportunities)
    return opp


@router.delete("/{opp_id}", status_code=204)
def delete_opportunity(
    opp_id: str,
    current_user: dict = Depends(auth_service.is_manager_or_admin),
):
    opportunities = db.get_opportunities()
    opp = next((o for o in opportunities if o["id"] == opp_id), None)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity non trovata")
    _check_owner(opp, current_user)
    if opp.get("stato") != "New":
        raise HTTPException(status_code=400,
                            detail="Puoi eliminare solo opportunity in stato New")
    db.save_opportunities([o for o in opportunities if o["id"] != opp_id])
