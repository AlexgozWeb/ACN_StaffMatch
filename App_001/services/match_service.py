import json
import uuid
from . import db, ai_service

SYSTEM_PROMPT = """Sei un esperto di staffing per progetti SAP/IT di Accenture Italy.
Ricevi i requisiti di un'opportunità e una lista di risorse disponibili con le loro skill e disponibilità.
Devi restituire SOLO un JSON valido (senza markdown, senza ```json) con questa struttura:
{
  "shortlist": [
    {
      "risorsa_id": "R001",
      "score": 85,
      "motivazione": "Spiegazione concisa in italiano (max 2 frasi)"
    }
  ]
}
Ordina per score decrescente. Includi solo risorse con score >= 40.
Il score va da 0 a 100 e considera: match skill (50%), disponibilità (30%), seniority (20%)."""

def run_matching(opportunity_id: str) -> list:
    opportunities = db.get_opportunities()
    opp = next((o for o in opportunities if o["id"] == opportunity_id), None)
    if not opp:
        raise ValueError(f"Opportunità {opportunity_id} non trovata")

    resources = db.get_resources()
    skills = {s["id"]: s for s in db.get_skills()}
    roles = {r["id"]: r for r in db.get_roles()}

    candidates = []
    for r in resources:
        disp = db.disponibilita_risorsa(r["id"])
        if disp <= 0:
            continue
        ruolo = roles.get(r["ruolo_id"], {})
        r_data = {
            "id": r["id"],
            "nome": f"{r['nome']} {r['cognome']}",
            "ruolo": ruolo.get("nome", ""),
            "seniority": ruolo.get("seniority", ""),
            "disponibilita": disp,
            "skills": [
                {"nome": skills[s["skill_id"]]["nome"], "livello": s["livello"]}
                for s in r.get("skill_ids", []) if s["skill_id"] in skills
            ],
            "lingue": r.get("lingue", []),
        }
        candidates.append(r_data)

    skill_names = [
        {"nome": skills[s["skill_id"]]["nome"], "livello_minimo": s["livello_minimo"]}
        for s in opp.get("skill_richieste", []) if s["skill_id"] in skills
    ]

    user_message = f"""
Opportunità: {opp['titolo']}
Cliente: {opp['cliente']}
Descrizione: {opp['descrizione']}
Skill richieste: {json.dumps(skill_names, ensure_ascii=False)}
Seniority minima: {opp['seniority_minima']}
Disponibilità richiesta: {opp['disponibilita_richiesta']}%
Numero risorse: {opp['numero_risorse']}

Risorse disponibili:
{json.dumps(candidates, ensure_ascii=False, indent=2)}
"""

    raw = ai_service.call_claude(SYSTEM_PROMPT, user_message)
    result = json.loads(raw)
    shortlist = result.get("shortlist", [])

    existing = db.get_match_results()
    existing = [m for m in existing if m["opportunity_id"] != opportunity_id]

    new_results = []
    for item in shortlist:
        entry = {
            "id": str(uuid.uuid4()),
            "opportunity_id": opportunity_id,
            "risorsa_id": item["risorsa_id"],
            "score": item["score"],
            "motivazione": item["motivazione"],
            "stato": "Proposed",
        }
        new_results.append(entry)

    db.save_match_results(existing + new_results)
    return new_results
