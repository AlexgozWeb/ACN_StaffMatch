import uuid
from fastapi import APIRouter, HTTPException, Depends
from models.schemas import OpportunityCreate
from services import auth_service, db

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
        "stato": "New",
    }
    opportunities = db.get_opportunities()
    opportunities.append(new_opp)
    db.save_opportunities(opportunities)
    return new_opp
