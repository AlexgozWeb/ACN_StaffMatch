import json
import uuid
from . import db, ai_service

SYSTEM_PROMPT = """Sei un esperto di staffing per progetti SAP/IT di Accenture Italy.
Ricevi i dettagli di uno slot risorsa di un'opportunità e una lista di candidati pre-filtrati.
Devi restituire SOLO un JSON valido (senza markdown, senza ```json) con questa struttura:
{
  "candidates": [
    {
      "risorsa_id": "R001",
      "score": 85,
      "motivazione": "Spiegazione concisa in italiano (max 2 frasi)"
    }
  ]
}
Ordina per score decrescente. Includi solo candidati con score >= 40.
Score 0-100: match skill richieste (50%), disponibilità vs % richiesta (30%), aderenza mansione/seniority (20%)."""


def run_matching(opportunity_id: str) -> list:
    opportunities = db.get_opportunities()
    opp = next((o for o in opportunities if o["id"] == opportunity_id), None)
    if not opp:
        raise ValueError(f"Opportunità {opportunity_id} non trovata")

    resources = db.get_resources()
    skills_map = {s["id"]: s for s in db.get_skills()}
    roles_map  = {r["id"]: r for r in db.get_roles()}

    skill_names = [
        {"nome": skills_map[s["skill_id"]]["nome"], "livello_minimo": s["livello_minimo"]}
        for s in opp.get("skill_richieste", []) if s["skill_id"] in skills_map
    ]

    all_results = []

    for slot_idx, slot in enumerate(opp.get("slot_risorse", [])):
        mansione_id  = slot["mansione_id"]
        perc_req     = slot["percentuale_allocazione"]
        mansione     = roles_map.get(mansione_id, {})
        mansione_nome = mansione.get("nome", mansione_id)
        seniority_target = mansione.get("seniority", "")

        candidates = []
        for r in resources:
            if r.get("id") == "R000":
                continue
            disp = db.disponibilita_risorsa(r["id"])
            if disp < perc_req:
                continue
            ruolo = roles_map.get(r["ruolo_id"], {})
            candidates.append({
                "id": r["id"],
                "nome": f"{r['nome']} {r['cognome']}",
                "mansione": ruolo.get("nome", ""),
                "seniority": ruolo.get("seniority", ""),
                "disponibilita": disp,
                "skills": [
                    {"nome": skills_map[s["skill_id"]]["nome"], "livello": s["livello"]}
                    for s in r.get("skill_ids", []) if s["skill_id"] in skills_map
                ],
                "lingue": r.get("lingue", []),
            })

        if not candidates:
            continue

        user_message = f"""
Opportunità: {opp['titolo']}
Cliente: {opp['cliente']}
Descrizione: {opp['descrizione']}
Skills richieste dal progetto: {json.dumps(skill_names, ensure_ascii=False)}

Slot {slot_idx + 1}: {mansione_nome} (Seniority target: {seniority_target})
Allocazione richiesta: {perc_req}%

Candidati disponibili:
{json.dumps(candidates, ensure_ascii=False, indent=2)}
"""

        raw = ai_service.call_claude(SYSTEM_PROMPT, user_message)
        result = json.loads(raw)

        for item in result.get("candidates", []):
            all_results.append({
                "id": str(uuid.uuid4()),
                "opportunity_id": opportunity_id,
                "slot_index": slot_idx,
                "risorsa_id": item["risorsa_id"],
                "score": item["score"],
                "motivazione": item["motivazione"],
                "stato": "Proposed",
            })

    existing = [m for m in db.get_match_results() if m["opportunity_id"] != opportunity_id]
    db.save_match_results(existing + all_results)
    return all_results
