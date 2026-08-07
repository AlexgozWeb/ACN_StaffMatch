import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from services import auth_service, db

router = APIRouter(prefix="/promotions", tags=["Promozioni"])


@router.post("/request/{opportunity_id}", status_code=201)
def request_promotion(
    opportunity_id: str,
    note: str = "",
    current_user: dict = Depends(auth_service.is_manager_or_admin),
):
    opps = db.get_opportunities()
    opp = next((o for o in opps if o["id"] == opportunity_id), None)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity non trovata")
    if opp.get("stato") not in ("New", "Active"):
        raise HTTPException(status_code=400, detail="Opportunity non in stato promuovibile")

    confirmed = [m for m in db.get_match_results()
                 if m["opportunity_id"] == opportunity_id and m["stato"] == "Confirmed"]
    if not confirmed:
        raise HTTPException(status_code=400,
                            detail="Nessuna risorsa confermata. Completa il matching prima.")

    slots = opp.get("slot_risorse", [])
    confirmed_by_slot = {}
    for m in confirmed:
        sidx = m.get("slot_index", 0)
        if sidx not in confirmed_by_slot:
            confirmed_by_slot[sidx] = m

    risorse_per_slot = [
        {
            "slot_index": sidx,
            "risorsa_id": m["risorsa_id"],
            "percentuale_allocazione": slots[sidx]["percentuale_allocazione"] if sidx < len(slots) else 100,
        }
        for sidx, m in confirmed_by_slot.items()
    ]

    pending = next((r for r in db.get_promotion_requests()
                    if r["opportunity_id"] == opportunity_id and r["stato"] == "Pending"), None)
    if pending:
        raise HTTPException(status_code=400, detail="Esiste già una richiesta di promozione in attesa.")

    new_req = {
        "id": f"PROM{str(uuid.uuid4())[:8].upper()}",
        "opportunity_id": opportunity_id,
        "opportunity_titolo": opp.get("titolo", ""),
        "opportunity_cliente": opp.get("cliente", ""),
        "requested_by_id": current_user["id"],
        "requested_by_nome": f"{current_user['nome']} {current_user['cognome']}",
        "requested_at": datetime.utcnow().isoformat(),
        "stato": "Pending",
        "note_manager": note,
        "note_executive": None,
        "reviewed_by_id": None,
        "reviewed_at": None,
        "risorse_per_slot": risorse_per_slot,
    }

    reqs = db.get_promotion_requests()
    reqs.append(new_req)
    db.save_promotion_requests(reqs)

    for o in opps:
        if o["id"] == opportunity_id:
            o["stato"] = "Pending"
            break
    db.save_opportunities(opps)

    return new_req


@router.get("/pending")
def get_pending(current_user: dict = Depends(auth_service.is_executive_or_admin)):
    reqs = db.get_promotion_requests()
    pending = [r for r in reqs if r["stato"] == "Pending"]
    resources = {r["id"]: r for r in db.get_resources()}
    result = []
    for req in pending:
        opp = next((o for o in db.get_opportunities() if o["id"] == req["opportunity_id"]), {})
        risorse_per_slot = req.get("risorse_per_slot", [])
        slots_dettaglio = [
            {
                "slot_index": s["slot_index"],
                "risorsa_id": s["risorsa_id"],
                "nome": f"{resources.get(s['risorsa_id'],{}).get('nome','')} {resources.get(s['risorsa_id'],{}).get('cognome','')}",
                "percentuale_allocazione": s["percentuale_allocazione"],
            }
            for s in risorse_per_slot
        ]
        result.append({**req, "slots_dettaglio": slots_dettaglio, "opportunity": opp})
    return result


@router.get("/")
def get_all(current_user: dict = Depends(auth_service.get_current_user)):
    return db.get_promotion_requests()


@router.patch("/{request_id}/review")
def review_promotion(
    request_id: str,
    decision: str,
    note_executive: str = "",
    current_user: dict = Depends(auth_service.is_executive_or_admin),
):
    if decision not in ("Approved", "Rejected"):
        raise HTTPException(status_code=400, detail="decision deve essere 'Approved' o 'Rejected'")

    reqs = db.get_promotion_requests()
    req = next((r for r in reqs if r["id"] == request_id), None)
    if not req:
        raise HTTPException(status_code=404, detail="Richiesta non trovata")
    if req["stato"] != "Pending":
        raise HTTPException(status_code=400, detail="Richiesta già elaborata")

    req["stato"] = decision
    req["note_executive"] = note_executive
    req["reviewed_by_id"] = current_user["id"]
    req["reviewed_at"] = datetime.utcnow().isoformat()
    db.save_promotion_requests(reqs)

    opps = db.get_opportunities()
    opp = next((o for o in opps if o["id"] == req["opportunity_id"]), None)

    if decision == "Approved" and opp:
        skills_req = opp.get("skill_richieste", [])
        skill_principale_id = skills_req[0]["skill_id"] if skills_req else ""
        skill_secondarie_ids = [s["skill_id"] for s in skills_req[1:]]

        new_project = {
            "id": f"PRJ{str(uuid.uuid4())[:8].upper()}",
            "nome": opp["titolo"],
            "cliente": opp["cliente"],
            "referente_it_cliente": opp.get("referente_it_cliente", {"nome": "", "cognome": ""}),
            "manager_id": req["requested_by_id"],
            "skill_principale_id": skill_principale_id,
            "skill_secondarie_ids": skill_secondarie_ids,
            "data_inizio": opp["data_inizio"],
            "data_fine_prevista": opp["data_fine_prevista"],
            "stato": "Active",
            "descrizione": opp.get("descrizione", f"Promosso da Opportunity {opp['id']}"),
        }
        projects = db.get_projects()
        projects.append(new_project)
        db.save_projects(projects)

        roles_map  = {r["id"]: r for r in db.get_roles()}
        slots      = opp.get("slot_risorse", [])
        allocations = db.get_allocations()
        for entry in req.get("risorse_per_slot", []):
            slot_data  = slots[entry["slot_index"]] if entry["slot_index"] < len(slots) else {}
            mansione   = roles_map.get(slot_data.get("mansione_id", ""), {})
            allocations.append({
                "id": f"ALL{str(uuid.uuid4())[:8].upper()}",
                "risorsa_id": entry["risorsa_id"],
                "progetto_id": new_project["id"],
                "percentuale": entry["percentuale_allocazione"],
                "data_inizio": opp["data_inizio"],
                "data_fine": opp["data_fine_prevista"],
                "ruolo_nel_progetto": mansione.get("nome", "Consultant"),
            })
        db.save_allocations(allocations)

        for o in opps:
            if o["id"] == opp["id"]:
                o["stato"] = "Active"
                break
        db.save_opportunities(opps)

        return {"message": "Opportunity promossa a Progetto Attivo", "project_id": new_project["id"]}

    elif decision == "Rejected" and opp:
        for o in opps:
            if o["id"] == opp["id"]:
                o["stato"] = "New"
                break
        db.save_opportunities(opps)
        return {"message": "Richiesta rifiutata — Opportunity riportata in stato New"}

    return {"message": f"Decisione registrata: {decision}"}
