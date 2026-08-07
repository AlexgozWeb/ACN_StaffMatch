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
        return {"opportunity_id": opportunity_id, "total_candidates": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{opportunity_id}/results")
def get_results(
    opportunity_id: str,
    current_user: dict = Depends(auth_service.get_current_user),
):
    all_results = [m for m in db.get_match_results() if m["opportunity_id"] == opportunity_id]
    if not all_results:
        raise HTTPException(status_code=404, detail="Nessun risultato. Lancia prima il matching.")

    opps = db.get_opportunities()
    opp  = next((o for o in opps if o["id"] == opportunity_id), None)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunità non trovata")

    resources = {r["id"]: r for r in db.get_resources()}
    roles     = {r["id"]: r for r in db.get_roles()}

    slots_out = []
    for slot_idx, slot in enumerate(opp.get("slot_risorse", [])):
        mansione = roles.get(slot["mansione_id"], {})
        slot_results = [m for m in all_results if m.get("slot_index") == slot_idx]
        candidates = []
        for m in sorted(slot_results, key=lambda x: x["score"], reverse=True):
            r    = resources.get(m["risorsa_id"], {})
            role = roles.get(r.get("ruolo_id", ""), {})
            candidates.append({
                **m,
                "risorsa_nome":  f"{r.get('nome','')} {r.get('cognome','')}",
                "ruolo_nome":    role.get("nome", ""),
                "seniority":     role.get("seniority", ""),
                "disponibilita": db.disponibilita_risorsa(m["risorsa_id"]),
            })
        slots_out.append({
            "slot_index":             slot_idx,
            "mansione_id":            slot["mansione_id"],
            "mansione_nome":          mansione.get("nome", slot["mansione_id"]),
            "percentuale_allocazione": slot["percentuale_allocazione"],
            "candidates":             candidates,
        })

    return {"opportunity_id": opportunity_id, "slots": slots_out}


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
