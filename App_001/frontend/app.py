import os
import streamlit as st
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="StaffMatch AI — Accenture Italy",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1a1a1a; }

    /* testo generico sidebar */
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] .stCaption { color: #cccccc !important; }

    /* pulsanti navigazione sidebar */
    [data-testid="stSidebar"] .stButton > button {
        background-color: #2d2d2d !important;
        color: #ffffff !important;
        border: 1px solid #444 !important;
        border-radius: 6px !important;
        text-align: left !important;
        font-weight: 400 !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #A100FF !important;
        border-color: #A100FF !important;
        color: #ffffff !important;
    }

    .main-title { color: #A100FF; font-size: 2rem; font-weight: 800; margin-bottom: 0; }
    .sub-title  { color: #666; font-size: 0.9rem; margin-top: 0; }
    div[data-testid="metric-container"] { background: #f8f8f8; border-radius: 8px; padding: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ── session state ──────────────────────────────────────────────────────────────
for k in ["token", "user", "page", "match_opp_id"]:
    if k not in st.session_state:
        st.session_state[k] = None

# ── helpers ────────────────────────────────────────────────────────────────────
def api(method: str, endpoint: str, **kwargs):
    headers = kwargs.pop("headers", {})
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        return requests.request(method, f"{BACKEND_URL}{endpoint}",
                                headers=headers, timeout=60, **kwargs)
    except requests.exceptions.ConnectionError:
        st.error("Backend non raggiungibile — assicurati che FastAPI sia in esecuzione su localhost:8000.")
        return None

def get_groups():
    if not st.session_state.user:
        return []
    if "cached_groups" in st.session_state:
        return st.session_state.cached_groups
    r = api("GET", "/role-groups/")
    if r and r.status_code == 200:
        all_g = r.json()
        ids = st.session_state.user.get("gruppo_ruolo_ids", [])
        names = [g["nome"] for g in all_g if g["id"] in ids]
        st.session_state.cached_groups = names
        return names
    return []

def can_write(groups):
    return any(g in groups for g in ["Manager", "Administrator"])

def is_admin(groups):
    return "Administrator" in groups

def nav(page: str):
    st.session_state.page = page
    st.rerun()

# ── LOGIN ──────────────────────────────────────────────────────────────────────
def show_login():
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<p class="main-title">🎯 StaffMatch AI</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-title">Staffing intelligente per progetti SAP/IT · Accenture Italy</p>',
                    unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("login"):
            email    = st.text_input("Email aziendale", placeholder="nome.cognome@accenture.com")
            password = st.text_input("Password", type="password")
            ok       = st.form_submit_button("Accedi →", use_container_width=True, type="primary")

        if ok:
            if not email or not password:
                st.error("Inserisci email e password.")
                return
            resp = api("POST", "/auth/login", json={"email": email, "password": password})
            if resp is None:
                return
            if resp.status_code == 200:
                data = resp.json()
                st.session_state.token = data["access_token"]
                me = api("GET", "/auth/me")
                if me and me.status_code == 200:
                    st.session_state.user = me.json()
                st.session_state.page = "dashboard"
                st.session_state.pop("cached_groups", None)
                st.rerun()
            else:
                st.error("Credenziali non valide.")

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
def show_sidebar(groups):
    with st.sidebar:
        st.markdown("## 🎯 StaffMatch AI")
        st.markdown("---")
        u = st.session_state.user or {}
        st.markdown(f"**{u.get('nome','')} {u.get('cognome','')}**")
        st.caption(u.get("email", ""))
        role_label = ("🔴 Administrator" if "Administrator" in groups
                      else "🔵 Manager" if "Manager" in groups
                      else "🟢 Employee")
        st.markdown(role_label)
        st.markdown("---")

        pages = [
            ("🏠", "Dashboard",       "dashboard"),
            ("👥", "Risorse",         "risorse"),
            ("📁", "Progetti",        "progetti"),
            ("🎯", "Opportunity",     "opportunity"),
            ("🤖", "Matching AI",     "matching"),
        ]
        if is_admin(groups):
            pages.append(("⚙️", "Amministrazione", "admin"))

        for icon, label, key in pages:
            active = "→ " if st.session_state.page == key else "   "
            if st.button(f"{active}{icon} {label}", use_container_width=True, key=f"nav_{key}"):
                st.session_state.page = key
                st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ── DASHBOARD ──────────────────────────────────────────────────────────────────
def show_dashboard(groups):
    st.markdown('<p class="main-title">🏠 Dashboard</p>', unsafe_allow_html=True)
    st.markdown("---")

    r_res  = api("GET", "/resources/")
    r_proj = api("GET", "/projects/")
    r_opp  = api("GET", "/opportunities/")

    resources    = r_res.json()  if r_res  and r_res.status_code  == 200 else []
    projects     = r_proj.json() if r_proj and r_proj.status_code == 200 else []
    opportunities= r_opp.json()  if r_opp  and r_opp.status_code  == 200 else []

    active_proj  = [p for p in projects     if p.get("stato") == "Active"]
    open_opp     = [o for o in opportunities if o.get("stato") == "New"]
    avail_res    = [r for r in resources     if r.get("disponibilita_percentuale", 0) >= 50]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Risorse GDL",       len(resources))
    c2.metric("📁 Progetti Attivi",   len(active_proj))
    c3.metric("🎯 Opportunity Aperte",len(open_opp))
    c4.metric("✅ Alta Disponibilità", len(avail_res))

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### 🎯 Opportunity Aperte")
        if open_opp:
            for o in open_opp[:5]:
                with st.container(border=True):
                    st.markdown(f"**{o.get('titolo','')}**")
                    st.caption(f"Cliente: {o.get('cliente','')}  |  Inizio: {o.get('data_inizio','')}")
                    skills_req = o.get("skill_richieste", [])
                    if skills_req:
                        ids = [s.get("skill_id","") for s in skills_req[:3]]
                        st.caption("Skills: " + ", ".join(ids))
        else:
            st.info("Nessuna opportunity aperta.")

    with col_b:
        st.markdown("### 👥 Top Disponibilità")
        sorted_res = sorted(resources, key=lambda r: r.get("disponibilita_percentuale", 0), reverse=True)
        for r in sorted_res[:6]:
            disp = int(r.get("disponibilita_percentuale", 0))
            c_name, c_prog = st.columns([2, 3])
            with c_name:
                st.markdown(f"**{r.get('nome','')} {r.get('cognome','')}**")
                st.caption(r.get("ruolo_nome", ""))
            with c_prog:
                color = "normal" if disp >= 50 else "off"
                st.progress(disp / 100, text=f"{disp}%")

# ── RISORSE ────────────────────────────────────────────────────────────────────
def show_risorse(groups):
    st.markdown('<p class="main-title">👥 Risorse GDL</p>', unsafe_allow_html=True)
    st.markdown("---")

    tab_labels = ["📋 Lista", "➕ Nuova Risorsa"] if can_write(groups) else ["📋 Lista"]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        resp = api("GET", "/resources/")
        if not resp or resp.status_code != 200:
            st.error("Errore nel caricamento risorse.")
            return
        resources = resp.json()

        col_s, col_f = st.columns([3, 1])
        with col_s:
            search = st.text_input("🔍 Cerca nome/cognome")
        with col_f:
            only_avail = st.checkbox("Solo disponibili (>0%)")

        if search:
            resources = [r for r in resources
                         if search.lower() in f"{r.get('nome','')} {r.get('cognome','')}".lower()]
        if only_avail:
            resources = [r for r in resources if r.get("disponibilita_percentuale", 0) > 0]

        if not resources:
            st.info("Nessuna risorsa trovata.")
        for r in resources:
            disp = int(r.get("disponibilita_percentuale", 0))
            icon = "🟢" if disp >= 50 else ("🟡" if disp > 0 else "🔴")
            label = f"{icon} **{r.get('nome','')} {r.get('cognome','')}** — {r.get('ruolo_nome','')} · {r.get('seniority','')}"
            with st.expander(label):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"📧 `{r.get('email','')}`")
                    st.markdown(f"🏷 Seniority: **{r.get('seniority','')}**")
                    st.markdown(f"💶 €{r.get('costo_orario', 0):.0f}/h")
                with c2:
                    st.markdown(f"**Disponibilità: {disp}%**")
                    st.progress(disp / 100)
                    lingue = r.get("lingue", [])
                    if lingue:
                        st.caption("🌐 " + " · ".join(lingue))
                with c3:
                    skills = r.get("skill_ids", [])
                    if skills:
                        skill_list = [s.get("skill_id", str(s)) if isinstance(s, dict) else str(s)
                                      for s in skills]
                        st.markdown("**Skills:** " + ", ".join(skill_list[:6]))

    if can_write(groups) and len(tabs) > 1:
        with tabs[1]:
            _form_crea_risorsa()

def _form_crea_risorsa():
    roles_r  = api("GET", "/roles/")
    skills_r = api("GET", "/skills/")
    groups_r = api("GET", "/role-groups/")

    roles  = roles_r.json()  if roles_r  and roles_r.status_code  == 200 else []
    skills = skills_r.json() if skills_r and skills_r.status_code == 200 else []
    rgroups= groups_r.json() if groups_r and groups_r.status_code == 200 else []

    role_map   = {r["nome"]: r["id"] for r in roles}
    skill_map  = {s["nome"]: s["id"] for s in skills}
    group_map  = {g["nome"]: g["id"] for g in rgroups}

    with st.form("form_risorsa", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            nome    = st.text_input("Nome *")
            email   = st.text_input("Email *")
        with c2:
            cognome = st.text_input("Cognome *")
            data_n  = st.date_input("Data di nascita")

        ruolo_sel  = st.selectbox("Ruolo *", list(role_map.keys()))
        skills_sel = st.multiselect("Skills", list(skill_map.keys()))
        livello    = st.slider("Livello skills (1=Junior … 5=Expert)", 1, 5, 3)

        lingue_options = ["Italiano", "Inglese", "Tedesco", "Francese", "Spagnolo"]
        lingue_sel = st.multiselect("Lingue", lingue_options, default=["Italiano", "Inglese"])

        group_sel  = st.selectbox("Gruppo Ruolo *", list(group_map.keys()))
        costo      = st.number_input("Costo orario €/h (opzionale, 0 = default ruolo)", 0.0, 500.0, 0.0)

        if st.form_submit_button("✅ Crea Risorsa", type="primary", use_container_width=True):
            if not all([nome, cognome, email, ruolo_sel]):
                st.error("Compila i campi obbligatori (*).")
                return
            payload = {
                "nome": nome, "cognome": cognome, "email": email,
                "data_nascita": str(data_n),
                "ruolo_id": role_map[ruolo_sel],
                "skill_ids": [{"skill_id": skill_map[s], "livello": livello} for s in skills_sel],
                "lingue": lingue_sel,
                "gruppo_ruolo_ids": [group_map[group_sel]],
            }
            if costo > 0:
                payload["costo_orario"] = costo
            r = api("POST", "/resources/", json=payload)
            if r and r.status_code == 201:
                st.success("✅ Risorsa creata con successo!")
            else:
                detail = r.json().get("detail", "Errore") if r else "Nessuna risposta"
                st.error(f"Errore: {detail}")

# ── PROGETTI ───────────────────────────────────────────────────────────────────
def show_progetti(groups):
    st.markdown('<p class="main-title">📁 Progetti</p>', unsafe_allow_html=True)
    st.markdown("---")

    tab_labels = ["📋 Lista", "➕ Nuovo Progetto"] if can_write(groups) else ["📋 Lista"]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        resp = api("GET", "/projects/")
        if not resp or resp.status_code != 200:
            st.error("Errore nel caricamento progetti.")
            return
        projects = resp.json()
        if not projects:
            st.info("Nessun progetto presente.")
        for p in projects:
            stato = p.get("stato", "")
            icon = "🟢" if stato == "Active" else ("🔴" if stato == "Closed" else "🟡")
            with st.expander(f"{icon} **{p.get('nome','')}** — {p.get('cliente','')}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Stato:** {stato}")
                    st.markdown(f"**Inizio:** {p.get('data_inizio','')}")
                    st.markdown(f"**Fine prevista:** {p.get('data_fine_prevista','')}")
                with c2:
                    ref = p.get("referente_it_cliente", {})
                    if ref:
                        st.markdown(f"**Referente:** {ref.get('nome','')} {ref.get('cognome','')}")
                    desc = p.get("descrizione","")
                    if desc:
                        st.caption(desc[:160])

    if can_write(groups) and len(tabs) > 1:
        with tabs[1]:
            _form_crea_progetto()

def _form_crea_progetto():
    skills_r = api("GET", "/skills/")
    skills   = skills_r.json() if skills_r and skills_r.status_code == 200 else []
    skill_map = {s["nome"]: s["id"] for s in skills}
    manager_id = (st.session_state.user or {}).get("id", "")

    with st.form("form_progetto", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            nome          = st.text_input("Nome progetto *")
            cliente       = st.text_input("Cliente *")
            ref_nome      = st.text_input("Referente cliente — Nome")
            data_inizio   = st.date_input("Data inizio")
        with c2:
            skill_princ   = st.selectbox("Skill principale *", list(skill_map.keys()))
            skill_sec     = st.multiselect("Skills secondarie", list(skill_map.keys()))
            ref_cognome   = st.text_input("Referente cliente — Cognome")
            data_fine     = st.date_input("Data fine prevista")

        descrizione = st.text_area("Descrizione")

        if st.form_submit_button("✅ Crea Progetto", type="primary", use_container_width=True):
            if not all([nome, cliente]):
                st.error("Compila i campi obbligatori (*).")
                return
            payload = {
                "nome": nome, "cliente": cliente,
                "referente_it_cliente": {"nome": ref_nome, "cognome": ref_cognome},
                "manager_id": manager_id,
                "skill_principale_id": skill_map.get(skill_princ, ""),
                "skill_secondarie_ids": [skill_map[s] for s in skill_sec],
                "data_inizio": str(data_inizio),
                "data_fine_prevista": str(data_fine),
                "descrizione": descrizione,
            }
            r = api("POST", "/projects/", json=payload)
            if r and r.status_code == 201:
                st.success("✅ Progetto creato!")
            else:
                detail = r.json().get("detail", "Errore") if r else "Nessuna risposta"
                st.error(f"Errore: {detail}")

# ── OPPORTUNITY ────────────────────────────────────────────────────────────────
def show_opportunity(groups):
    st.markdown('<p class="main-title">🎯 Opportunity</p>', unsafe_allow_html=True)
    st.markdown("---")

    tab_labels = ["📋 Lista", "➕ Nuova Opportunity"] if can_write(groups) else ["📋 Lista"]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        resp = api("GET", "/opportunities/")
        if not resp or resp.status_code != 200:
            st.error("Errore nel caricamento opportunity.")
            return
        opportunities = resp.json()
        if not opportunities:
            st.info("Nessuna opportunity presente.")
        for o in opportunities:
            stato = o.get("stato","")
            icon  = "🟢" if stato == "New" else ("🔵" if stato == "Active" else "🔴")
            with st.expander(f"{icon} **{o.get('titolo','')}** — {o.get('cliente','')}  [{stato}]"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Inizio:** {o.get('data_inizio','')}")
                    st.markdown(f"**Fine prevista:** {o.get('data_fine_prevista','')}")
                    st.markdown(f"**Risorse richieste:** {o.get('numero_risorse','')}")
                    st.markdown(f"**Disponibilità min:** {o.get('disponibilita_richiesta','')}%")
                    st.markdown(f"**Seniority min:** {o.get('seniority_minima','')}")
                with c2:
                    for s in o.get("skill_richieste", []):
                        st.markdown(f"  • `{s.get('skill_id','')}` lv.{s.get('livello_minimo','')}")
                    desc = o.get("descrizione","")
                    if desc:
                        st.caption(desc[:160])

                if can_write(groups) and stato == "New":
                    if st.button("🤖 Avvia Matching AI", key=f"goto_match_{o['id']}"):
                        st.session_state.match_opp_id = o["id"]
                        st.session_state.page = "matching"
                        st.rerun()

    if can_write(groups) and len(tabs) > 1:
        with tabs[1]:
            _form_crea_opportunity()

def _form_crea_opportunity():
    skills_r  = api("GET", "/skills/")
    skills    = skills_r.json() if skills_r and skills_r.status_code == 200 else []
    skill_map = {s["nome"]: s["id"] for s in skills}
    manager_id= (st.session_state.user or {}).get("id", "")

    seniority_options = ["Junior", "Analyst", "Consultant", "Senior Consultant", "Manager", "Senior Manager"]

    with st.form("form_opp", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            titolo         = st.text_input("Titolo *")
            cliente        = st.text_input("Cliente *")
            ref_nome       = st.text_input("Referente cliente — Nome")
            data_inizio    = st.date_input("Data inizio")
            num_risorse    = st.number_input("Risorse richieste", 1, 20, 1)
        with c2:
            seniority_min  = st.selectbox("Seniority minima", seniority_options)
            disponib_req   = st.slider("Disponibilità richiesta (%)", 10, 100, 50, 10)
            ref_cognome    = st.text_input("Referente cliente — Cognome")
            data_fine      = st.date_input("Data fine prevista")

        skills_sel = st.multiselect("Skills richieste *", list(skill_map.keys()))
        livello_min= st.slider("Livello minimo skills (1–5)", 1, 5, 3)
        descrizione= st.text_area("Descrizione")

        if st.form_submit_button("✅ Crea Opportunity", type="primary", use_container_width=True):
            if not all([titolo, cliente, skills_sel]):
                st.error("Compila i campi obbligatori (*).")
                return
            payload = {
                "titolo": titolo, "cliente": cliente,
                "referente_it_cliente": {"nome": ref_nome, "cognome": ref_cognome},
                "manager_id": manager_id,
                "skill_richieste": [{"skill_id": skill_map[s], "livello_minimo": livello_min}
                                    for s in skills_sel],
                "seniority_minima": seniority_min,
                "disponibilita_richiesta": disponib_req,
                "numero_risorse": num_risorse,
                "data_inizio": str(data_inizio),
                "data_fine_prevista": str(data_fine),
                "descrizione": descrizione,
            }
            r = api("POST", "/opportunities/", json=payload)
            if r and r.status_code == 201:
                st.success("✅ Opportunity creata!")
            else:
                detail = r.json().get("detail", "Errore") if r else "Nessuna risposta"
                st.error(f"Errore: {detail}")

# ── MATCHING AI ────────────────────────────────────────────────────────────────
def show_matching(groups):
    st.markdown('<p class="main-title">🤖 Matching AI</p>', unsafe_allow_html=True)
    st.caption("Powered by **Claude Sonnet 4.6** via SAP AI Core")
    st.markdown("---")

    r_opp = api("GET", "/opportunities/")
    opps  = r_opp.json() if r_opp and r_opp.status_code == 200 else []

    if not opps:
        st.info("Nessuna opportunity presente.")
        return

    opp_map = {o["titolo"]: o["id"] for o in opps}

    presel_id = st.session_state.match_opp_id
    presel_title = next((t for t, i in opp_map.items() if i == presel_id), None) if presel_id else None
    default_idx  = list(opp_map.keys()).index(presel_title) if presel_title and presel_title in opp_map else 0

    sel_title = st.selectbox("Seleziona Opportunity", list(opp_map.keys()), index=default_idx)
    sel_id    = opp_map[sel_title]
    st.session_state.match_opp_id = sel_id

    if can_write(groups):
        if st.button("🚀 Esegui Matching AI", type="primary"):
            with st.spinner("🤖 Claude sta analizzando le risorse disponibili… (10–20 sec)"):
                r = api("POST", f"/match/{sel_id}")
                if r and r.status_code == 200:
                    st.success("✅ Matching completato!")
                    st.rerun()
                else:
                    detail = r.json().get("detail","Errore") if r else "Nessuna risposta"
                    st.error(f"Errore: {detail}")

    st.markdown("---")
    st.markdown("### 📊 Shortlist")

    r_res = api("GET", f"/match/{sel_id}/results")
    if r_res is None:
        return
    if r_res.status_code == 404:
        st.info("Nessun risultato. Esegui prima il matching.")
        return
    if r_res.status_code != 200:
        st.error("Errore nel caricamento risultati.")
        return

    data      = r_res.json()
    shortlist = data.get("shortlist", [])

    if not shortlist:
        st.info("Nessuna risorsa nella shortlist.")
        return

    for i, item in enumerate(shortlist, 1):
        score  = item.get("score", 0)
        stato  = item.get("stato", "Proposed")
        nome   = item.get("risorsa_nome", "")
        motiv  = item.get("motivazione", "")
        disp   = item.get("disponibilita", 0)
        rid    = item.get("id","")

        score_color = "🟢" if score >= 80 else ("🟡" if score >= 60 else "🔴")
        status_icon = {"Confirmed": "✅", "Rejected": "❌", "Proposed": "⏳"}.get(stato, "⏳")

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
            with c1:
                st.markdown(f"**{i}. {nome}**")
                st.caption(motiv[:120] + "…" if len(motiv) > 120 else motiv)
            with c2:
                st.markdown(f"{score_color} **{score}/100**")
                st.progress(score / 100)
            with c3:
                st.markdown(f"Disponibilità: **{int(disp)}%**")
                st.markdown(f"Stato: {status_icon} {stato}")
            with c4:
                if can_write(groups) and stato == "Proposed":
                    col_ok, col_no = st.columns(2)
                    with col_ok:
                        if st.button("✅", key=f"ok_{rid}", help="Conferma"):
                            api("PATCH", f"/match/{sel_id}/results/{rid}",
                                params={"stato": "Confirmed"})
                            st.rerun()
                    with col_no:
                        if st.button("❌", key=f"no_{rid}", help="Rifiuta"):
                            api("PATCH", f"/match/{sel_id}/results/{rid}",
                                params={"stato": "Rejected"})
                            st.rerun()

# ── ADMIN ──────────────────────────────────────────────────────────────────────
def show_admin(groups):
    st.markdown('<p class="main-title">⚙️ Amministrazione</p>', unsafe_allow_html=True)
    st.markdown("---")

    tab_users, tab_groups = st.tabs(["👥 Assegna Ruoli", "🔐 Gruppi Ruolo"])

    with tab_users:
        st.markdown("### Assegna Gruppo Ruolo a una Risorsa")
        r_res = api("GET", "/resources/")
        r_grp = api("GET", "/role-groups/")
        resources  = r_res.json() if r_res and r_res.status_code == 200 else []
        role_groups= r_grp.json() if r_grp and r_grp.status_code == 200 else []

        res_map = {f"{r['nome']} {r['cognome']} ({r['email']})": r["id"] for r in resources}
        grp_map = {g["nome"]: g["id"] for g in role_groups}

        sel_res = st.selectbox("Risorsa", list(res_map.keys()))
        sel_grps= st.multiselect("Gruppi da assegnare", list(grp_map.keys()))

        if st.button("Aggiorna Gruppi", type="primary"):
            rid     = res_map[sel_res]
            gids    = [grp_map[g] for g in sel_grps]
            r       = api("PATCH", f"/role-groups/resources/{rid}/groups", json=gids)
            if r and r.status_code == 200:
                st.success("✅ Gruppi aggiornati!")
                st.session_state.pop("cached_groups", None)
            else:
                detail = r.json().get("detail","Errore") if r else "Nessuna risposta"
                st.error(f"Errore: {detail}")

    with tab_groups:
        st.markdown("### Gruppi Ruolo Definiti")
        r_grp2 = api("GET", "/role-groups/")
        if r_grp2 and r_grp2.status_code == 200:
            for g in r_grp2.json():
                with st.expander(f"**{g['nome']}** — {g.get('descrizione','')}"):
                    st.markdown(f"ID: `{g['id']}`")
                    ruoli = g.get("ruoli_ids", [])
                    if ruoli:
                        st.markdown("Ruoli: " + ", ".join(ruoli))

# ── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    if not st.session_state.token:
        show_login()
        return

    groups = get_groups()
    show_sidebar(groups)

    page = st.session_state.page or "dashboard"

    if page == "dashboard":
        show_dashboard(groups)
    elif page == "risorse":
        show_risorse(groups)
    elif page == "progetti":
        show_progetti(groups)
    elif page == "opportunity":
        show_opportunity(groups)
    elif page == "matching":
        show_matching(groups)
    elif page == "admin":
        show_admin(groups)

main()
