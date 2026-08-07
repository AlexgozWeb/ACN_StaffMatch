from fastapi import APIRouter, HTTPException, Depends
from services import auth_service, db, match_service

router = APIRouter(prefix="/match", tags=["Matching AI"])

@router.post("/{opportunity_id}")
def run_match(
    opportunity_id: str,
    current_user: dict = Depends(auth_service.is_manager_or_admin),
):
    opps = db.get_opportunities()
    if not any(o["id"] == opportunity_id for o in opps):
        raise HTTPException(status_code=404, detail="Opportunità non trovata")
    try:
        results = match_service.run_matching(opportunity_id)
        return {"opportunity_id": opportunity_id, "shortlist": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{opportunity_id}/results")
def get_results(
    opportunity_id: str,
    current_user: dict = Depends(auth_service.get_current_user),
):
    results = [m for m in db.get_match_results() if m["opportunity_id"] == opportunity_id]
    if not results:
        raise HTTPException(status_code=404, detail="Nessun risultato trovato. Lancia prima il matching.")
    resources = {r["id"]: r for r in db.get_resources()}
    shortlist = []
    for m in sorted(results, key=lambda x: x["score"], reverse=True):
        r = resources.get(m["risorsa_id"], {})
        shortlist.append({
            **m,
            "risorsa_nome": f"{r.get('nome','')} {r.get('cognome','')}",
            "disponibilita": db.disponibilita_risorsa(m["risorsa_id"]),
        })
    return {"opportunity_id": opportunity_id, "shortlist": shortlist}

@router.patch("/{opportunity_id}/results/{result_id}")
def update_result_status(
    opportunity_id: str,
    result_id: str,
    stato: str,
    current_user: dict = Depends(auth_service.is_manager_or_admin),
):
    if stato not in ("Confirmed", "Rejected", "Proposed"):
        raise HTTPException(status_code=400, detail="Stato non valido")
    results = db.get_match_results()
    updated = False
    for m in results:
        if m["id"] == result_id and m["opportunity_id"] == opportunity_id:
            m["stato"] = stato
            updated = True
            break
    if not updated:
        raise HTTPException(status_code=404, detail="Risultato non trovato")
    db.save_match_results(results)
    return {"message": f"Stato aggiornato a {stato}"}
