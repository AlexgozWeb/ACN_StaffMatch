# StaffMatch AI — Briefing per Claude Code

## Contesto
Stiamo sviluppando **StaffMatch AI**, un'applicazione Python/FastAPI per la gestione intelligente dello staffing in Accenture Italy. Il progetto fa parte di un contest interno GenAI su SAP BTP.

## Obiettivo dell'app
Un Manager inserisce una nuova opportunità (progetto) e l'AI suggerisce automaticamente le risorse GDL più adatte, calcolando un **match score** basato su:
- Skill funzionali e tecniche della risorsa
- Disponibilità attuale (% allocazione sui progetti in corso)
- Seniority

## Architettura target (da `staffmatch_architettura_sap_btp.png`)

```
Manager → SAP Build Work Zone
            ↓
    Cloud Foundry Backend (FastAPI)
            ↓
    SAP AI Core (Claude Sonnet 4.6) — calcola match score
            ↓
    Knowledge Base (dati mock JSON in locale, HANA Cloud su BTP)
    ├── Risorse GDL (skill funzionali e tecniche)
    ├── Progetti in corso (assegnazioni, %, date)
    └── Opportunità (stato: New / Active)
            ↓
    Shortlist risorse candidate (ranked)
            ↓
    SAP Build Process Automation (notifica Manager)
            ↓
    Confermato → Piano di staffing
    Rifiutato  → Re-match automatico
```

## Stack tecnologico
- **Backend:** Python 3.10+, FastAPI, Uvicorn
- **AI:** SAP AI Core con modello `anthropic--claude-4.6-sonnet`
- **Auth AI:** OAuth2 client_credentials verso SAP AI Core
- **Dati:** JSON mock in locale (fase 1), SAP HANA Cloud (fase 2 su BTP)
- **Deploy target:** SAP BTP Cloud Foundry, Space `Group_Five`, Subaccount `Accenture_SAPDiscover_ITALY_INTERNAL`

## Credenziali SAP AI Core (già verificate e funzionanti)
Salvate nel file `.env` nella root del progetto:

```env
AICORE_AUTH_URL=https://accenture-genai-finance-it.authentication.eu10.hana.ondemand.com
AICORE_BASE_URL=https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com
AICORE_CLIENT_ID=sb-af5178da-e562-4920-88ce-7420bb0a47e6!b579810|aicore!b540
AICORE_CLIENT_SECRET=ba6c626e-4b21-4c75-b72c-127ab26d006e$w_UXisD261ymj4UTt3QNrL5X7yhFLv8Q_s_74pWr870=
AICORE_RESOURCE_GROUP=group-five
```

## Struttura del progetto da creare

```
C:\CLAUDE\ACN_StaffMatch\App_001\
│
├── main.py                  # FastAPI app — entry point
├── requirements.txt         # dipendenze Python
├── .env                     # credenziali (NON committare su git)
├── .gitignore               # esclude .env e __pycache__
├── manifest.yml             # deploy su SAP BTP Cloud Foundry
├── Procfile                 # comando di avvio per Cloud Foundry
│
├── routers/
│   ├── __init__.py
│   ├── opportunities.py     # CRUD opportunità
│   ├── resources.py         # CRUD risorse GDL
│   └── matching.py          # endpoint match score AI
│
├── services/
│   ├── __init__.py
│   ├── ai_service.py        # autenticazione + chiamate SAP AI Core
│   └── match_service.py     # logica di matching e ranking
│
├── models/
│   ├── __init__.py
│   └── schemas.py           # modelli Pydantic
│
└── data/
    ├── resources.json        # mock: 10 risorse GDL con skill e disponibilità
    ├── projects.json         # mock: 5 progetti in corso con allocazioni
    └── opportunities.json    # mock: 3 opportunità (stato New)
```

## Cosa deve fare `ai_service.py`

1. **Ottenere il token OAuth2** da `AICORE_AUTH_URL` con `grant_type=client_credentials`
2. **Chiamare il modello** `anthropic--claude-4.6-sonnet` tramite endpoint:
   ```
   POST {AICORE_BASE_URL}/v2/inference/deployments/{deployment_id}/chat/completions
   Header: AI-Resource-Group: group-five
   Header: Authorization: Bearer {token}
   ```
3. **Prompt di sistema** per il matching:
   - Riceve: requisiti dell'opportunità + lista risorse con skill e disponibilità
   - Restituisce: JSON con shortlist ranked (risorsa, match_score 0-100, motivazione)

## Dati mock da generare

### `data/resources.json` — 10 risorse GDL Accenture
Ogni risorsa deve avere:
```json
{
  "id": "R001",
  "nome": "Mario Rossi",
  "ruolo": "Senior Consultant",
  "seniority": "Senior",
  "skill_funzionali": ["SAP FI", "SAP CO", "Controlling"],
  "skill_tecniche": ["ABAP", "SAP BTP", "Python"],
  "disponibilita_percentuale": 50,
  "progetti_attivi": ["P001"],
  "lingua": ["italiano", "inglese"]
}
```

### `data/projects.json` — 5 progetti in corso
```json
{
  "id": "P001",
  "nome": "Digital Finance Transformation",
  "cliente": "Banca XYZ",
  "data_fine": "2025-12-31",
  "risorse_allocate": [
    {"risorsa_id": "R001", "percentuale": 50}
  ]
}
```

### `data/opportunities.json` — 3 opportunità
```json
{
  "id": "OPP001",
  "titolo": "SAP S/4HANA Finance Implementation",
  "cliente": "Industria ABC",
  "skill_richieste": ["SAP FI", "SAP CO", "S/4HANA"],
  "seniority_minima": "Senior",
  "disponibilita_richiesta": 100,
  "data_inizio": "2025-10-01",
  "stato": "New"
}
```

## Endpoint FastAPI da implementare

| Method | Path | Descrizione |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/opportunities` | Lista opportunità |
| POST | `/opportunities` | Crea nuova opportunità |
| GET | `/resources` | Lista risorse GDL |
| POST | `/match/{opportunity_id}` | Calcola match score AI per un'opportunità |
| GET | `/match/{opportunity_id}/results` | Risultati shortlist |

## Fase 1 — Sviluppo locale
- Avvia con: `uvicorn main:app --reload --port 8000`
- Testa su: `http://localhost:8000/docs` (Swagger UI automatico di FastAPI)

## Fase 2 — Deploy su SAP BTP (dopo che l'app funziona in locale)
Il `manifest.yml` per Cloud Foundry:
```yaml
applications:
  - name: staffmatch-ai-backend
    memory: 512M
    instances: 1
    buildpacks:
      - python_buildpack
    command: pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port $PORT
    env:
      AICORE_AUTH_URL: https://accenture-genai-finance-it.authentication.eu10.hana.ondemand.com
      AICORE_BASE_URL: https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com
      AICORE_CLIENT_ID: sb-af5178da-e562-4920-88ce-7420bb0a47e6!b579810|aicore!b540
      AICORE_CLIENT_SECRET: ba6c626e-4b21-4c75-b72c-127ab26d006e$w_UXisD261ymj4UTt3QNrL5X7yhFLv8Q_s_74pWr870=
      AICORE_RESOURCE_GROUP: group-five
```

## Note importanti per Claude Code
1. **Inizia dalla Fase 1** — app completamente funzionante in locale con dati mock
2. **Non usare database reali** in questa fase — solo JSON file
3. **Testa ogni endpoint** prima di passare al successivo
4. **Il token OAuth2 scade** — `ai_service.py` deve gestire il refresh automatico
5. **Usa `python-dotenv`** per caricare le variabili da `.env`
6. **CORS abilitato** — servirà per il frontend in futuro
