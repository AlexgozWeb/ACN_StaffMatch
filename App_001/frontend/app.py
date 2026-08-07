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
        st.error(f"Backend non raggiungibile ({BACKEND_URL}).")
        return None
    except Exception as _e:
        st.error(f"Errore chiamata API: {type(_e).__name__}: {_e}")
        return None

def get_groups():
    if not st.session_state.user:
        return []
    if "cached_groups" in st.session_state:
        return st.session_state.cached_groups
    groups = st.session_state.user.get("gruppi", [])
    st.session_state.cached_groups = groups
    return groups

def can_write(groups):
    return any(g in groups for g in ["Manager", "Executive", "Administrator"])

def is_executive_or_admin(groups):
    return any(g in groups for g in ["Executive", "Administrator"])

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
                      else "🟣 Executive"  if "Executive"      in groups
                      else "🔵 Manager"    if "Manager"        in groups
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
        if is_executive_or_admin(groups):
            pages.append(("📋", "Approvazioni", "approvazioni"))
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
        resp     = api("GET", "/resources/")
        sk_resp  = api("GET", "/skills/")
        if not resp or resp.status_code != 200:
            st.error("Errore nel caricamento risorse.")
            return
        resources = resp.json()
        skill_id_map_res = {s["id"]: s["nome"] for s in (sk_resp.json() if sk_resp and sk_resp.status_code == 200 else [])}

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
                    st.markdown(f"🏷 Mansione: **{r.get('ruolo_nome','')}** ({r.get('seniority','')})")
                    st.markdown(f"💶 €{r.get('costo_orario', 0):.0f}/h")
                with c2:
                    st.markdown(f"**Disponibilità: {disp}%**")
                    st.progress(disp / 100)
                    lingue = r.get("lingue", [])
                    if lingue:
                        st.caption("🌐 " + " · ".join(lingue))
                with c3:
                    skills_raw = r.get("skill_ids", [])
                    if skills_raw:
                        st.markdown("**Skills:**")
                        for sk in skills_raw:
                            if isinstance(sk, dict):
                                sk_nome = skill_id_map_res.get(sk.get("skill_id",""), sk.get("skill_id",""))
                                sk_lv   = sk.get("livello", "?")
                                st.caption(f"  • {sk_nome} — lv.**{sk_lv}**/5")

    if can_write(groups) and len(tabs) > 1:
        with tabs[1]:
            _form_crea_risorsa()

def _api_detail(r, fallback="Nessuna risposta dal backend"):
    if r is None:
        return fallback
    try:
        return r.json().get("detail", f"HTTP {r.status_code}")
    except Exception:
        return f"HTTP {r.status_code}: {r.text[:200]}"

def _form_crea_risorsa():
    import datetime as _dt
    if st.session_state.pop("cr_last_success", False):
        st.success("✅ Risorsa creata con successo!")
    if "cr_last_error" in st.session_state:
        st.error(f"Errore: {st.session_state.pop('cr_last_error')}")

    mansioni_r = api("GET", "/mansioni/")
    skills_r   = api("GET", "/skills/")
    groups_r   = api("GET", "/roles/")

    mansioni  = mansioni_r.json() if mansioni_r and mansioni_r.status_code == 200 else []
    skills    = skills_r.json()   if skills_r   and skills_r.status_code   == 200 else []
    rgroups   = groups_r.json()   if groups_r   and groups_r.status_code   == 200 else []

    mansione_map = {m["nome"]: m["id"] for m in mansioni}
    skill_map    = {s["nome"]: s["id"] for s in skills}
    group_map    = {g["nome"]: g["id"] for g in rgroups}

    c1, c2 = st.columns(2)
    with c1:
        nome  = st.text_input("Nome *", key="cr_nome")
        email = st.text_input("Email *", key="cr_email")
    with c2:
        cognome = st.text_input("Cognome *", key="cr_cognome")
        data_n  = st.date_input("Data di nascita", value=None, format="YYYY-MM-DD",
                                min_value=_dt.date(1940, 1, 1), key="cr_datanascita")

    ruolo_sel = st.selectbox("Mansione *", list(mansione_map.keys()), key="cr_mansione")

    skills_sel = st.multiselect("Skills", list(skill_map.keys()), key="cr_skills")
    if skills_sel:
        st.markdown("**Livello per ogni skill:**")
        cols_sk = st.columns(min(len(skills_sel), 3))
        for i, s in enumerate(skills_sel):
            with cols_sk[i % 3]:
                st.slider(s, 1, 5, 3, key=f"cr_slv_{s}",
                          help="1 = Base · 3 = Intermedio · 5 = Expert")

    lingue_options = ["Italiano", "Inglese", "Tedesco", "Francese", "Spagnolo"]
    if "cr_lingue" not in st.session_state:
        st.session_state["cr_lingue"] = ["Italiano", "Inglese"]
    lingue_sel = st.multiselect("Lingue", lingue_options, key="cr_lingue")

    c3, c4 = st.columns(2)
    with c3:
        group_sel = st.selectbox("Ruolo autorizzativo *", list(group_map.keys()), key="cr_gruppo")
    with c4:
        costo = st.number_input("Costo orario €/h (0 = default ruolo)", 0.0, 500.0, 0.0, key="cr_costo")

    if st.button("✅ Crea Risorsa", type="primary", use_container_width=True, key="cr_submit"):
        nome_v  = st.session_state.get("cr_nome","").strip()
        cogn_v  = st.session_state.get("cr_cognome","").strip()
        email_v = st.session_state.get("cr_email","").strip()
        if not all([nome_v, cogn_v, email_v, ruolo_sel]):
            st.error("Compila i campi obbligatori (*).")
            return
        sel_skills = st.session_state.get("cr_skills", [])
        skill_ids  = [{"skill_id": skill_map[s], "livello": st.session_state.get(f"cr_slv_{s}", 3)}
                      for s in sel_skills]
        payload = {
            "nome": nome_v, "cognome": cogn_v, "email": email_v,
            "data_nascita": str(st.session_state.get("cr_datanascita", _dt.date.today())),
            "ruolo_id": mansione_map[ruolo_sel],
            "skill_ids": skill_ids,
            "lingue": [l.lower() for l in st.session_state.get("cr_lingue", [])],
            "gruppo_ruolo_ids": [group_map[group_sel]],
        }
        costo_v = st.session_state.get("cr_costo", 0.0)
        if costo_v > 0:
            payload["costo_orario"] = costo_v
        r = api("POST", "/resources/", json=payload)
        if r and r.status_code == 201:
            for k in [k2 for k2 in list(st.session_state.keys()) if k2.startswith("cr_")]:
                del st.session_state[k]
            st.session_state["cr_last_success"] = True
            st.rerun()
        else:
            if r is None:
                detail = "Nessuna risposta dal backend"
            else:
                try:
                    detail = r.json().get("detail", f"HTTP {r.status_code}")
                except Exception:
                    detail = f"HTTP {r.status_code}: {r.text[:200]}"
            st.session_state["cr_last_error"] = detail
            st.rerun()

# ── PROGETTI ───────────────────────────────────────────────────────────────────
def show_progetti(groups):
    st.markdown('<p class="main-title">📁 Progetti</p>', unsafe_allow_html=True)
    st.markdown("---")

    tab_labels = ["📋 Lista", "➕ Nuovo Progetto"] if can_write(groups) else ["📋 Lista"]
    tabs = st.tabs(tab_labels)
    current_uid = (st.session_state.user or {}).get("id", "")

    with tabs[0]:
        resp = api("GET", "/projects/")
        if not resp or resp.status_code != 200:
            st.error("Errore nel caricamento progetti.")
            return
        projects = resp.json()
        if not projects:
            st.info("Nessun progetto presente.")

        for p in projects:
            stato   = p.get("stato", "")
            icon    = "🟢" if stato == "Active" else ("🔴" if stato == "Closed" else "🟡")
            is_owner= p.get("manager_id") == current_uid or is_admin(groups)

            with st.expander(f"{icon} **{p.get('nome','')}** — {p.get('cliente','')}  [{stato}]  ({p.get('num_risorse',0)} risorse)"):
                # dettaglio progetto
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

                # risorse allocate (carica dettaglio)
                if stato == "Active":
                    st.markdown("**Risorse allocate:**")
                    det_r = api("GET", f"/projects/{p['id']}")
                    allocs = det_r.json().get("allocazioni",[]) if det_r and det_r.status_code == 200 else []
                    res_map = {r["id"]: r for r in (api("GET","/resources/").json() if api("GET","/resources/") else [])}

                    if allocs:
                        for a in allocs:
                            r_info = res_map.get(a.get("risorsa_id",""), {})
                            r_nome = f"{r_info.get('nome','')} {r_info.get('cognome','')}"
                            ac1, ac2, ac3 = st.columns([3,2,2])
                            with ac1:
                                st.markdown(f"• **{r_nome}** — {a.get('ruolo_nel_progetto','')}")
                            with ac2:
                                st.markdown(f"📊 {a.get('percentuale',0)}%")
                            with ac3:
                                if is_owner and can_write(groups):
                                    if st.button("🔓 Rilascia", key=f"rel_{a['id']}"):
                                        pr = api("POST", f"/project-changes/propose/{p['id']}",
                                                 json={"change_type":"remove_resource",
                                                       "payload":{"allocation_id": a["id"]},
                                                       "note_manager":""})
                                        if pr and pr.status_code == 201:
                                            st.success("Richiesta di rilascio inviata all'Executive.")
                                        else:
                                            detail = _api_detail(pr)
                                            st.error(f"Errore: {detail}")
                    else:
                        st.caption("Nessuna risorsa allocata.")

                    # aggiungi risorsa
                    if is_owner and can_write(groups):
                        with st.expander("➕ Proponi aggiunta risorsa"):
                            res_resp2 = api("GET", "/resources/")
                            all_res = res_resp2.json() if res_resp2 and res_resp2.status_code == 200 else []
                            allocated_ids = {a.get("risorsa_id") for a in allocs}
                            free_res = [r for r in all_res if r["id"] not in allocated_ids]
                            if free_res:
                                res_opts = {f"{r['nome']} {r['cognome']} ({r.get('ruolo_nome','')})": r["id"] for r in free_res}
                                with st.form(f"add_res_{p['id']}"):
                                    sel_res   = st.selectbox("Risorsa", list(res_opts.keys()))
                                    perc      = st.slider("Percentuale allocazione", 10, 100, 50, 10)
                                    ruolo_prj = st.text_input("Ruolo nel progetto", value="Consultant")
                                    note_add  = st.text_input("Note (opzionale)")
                                    if st.form_submit_button("📤 Proponi", type="primary"):
                                        proj_det = api("GET", f"/projects/{p['id']}")
                                        d_ini = proj_det.json().get("data_inizio","") if proj_det else ""
                                        d_fin = proj_det.json().get("data_fine_prevista","") if proj_det else ""
                                        pr = api("POST", f"/project-changes/propose/{p['id']}",
                                                 json={"change_type":"add_resource",
                                                       "payload":{"risorsa_id": res_opts[sel_res],
                                                                  "percentuale": perc,
                                                                  "data_inizio": d_ini,
                                                                  "data_fine": d_fin,
                                                                  "ruolo_nel_progetto": ruolo_prj},
                                                       "note_manager": note_add})
                                        if pr and pr.status_code == 201:
                                            st.success("Richiesta inviata all'Executive!")
                                        else:
                                            detail = _api_detail(pr)
                                            st.error(f"Errore: {detail}")

                        # modifica info progetto
                        with st.expander("✏️ Proponi modifica info progetto"):
                            with st.form(f"edit_prj_{p['id']}"):
                                new_nome  = st.text_input("Nome", value=p.get("nome",""))
                                new_cli   = st.text_input("Cliente", value=p.get("cliente",""))
                                new_fine  = st.text_input("Data fine (YYYY-MM-DD)", value=p.get("data_fine_prevista",""))
                                new_desc  = st.text_area("Descrizione", value=p.get("descrizione",""))
                                note_edit = st.text_input("Note per l'Executive (opzionale)")
                                if st.form_submit_button("📤 Proponi modifica", type="primary"):
                                    pr = api("POST", f"/project-changes/propose/{p['id']}",
                                             json={"change_type":"update_info",
                                                   "payload":{"nome":new_nome,"cliente":new_cli,
                                                              "data_fine_prevista":new_fine,
                                                              "descrizione":new_desc},
                                                   "note_manager": note_edit})
                                    if pr and pr.status_code == 201:
                                        st.success("Richiesta di modifica inviata all'Executive!")
                                    else:
                                        detail = _api_detail(pr)
                                        st.error(f"Errore: {detail}")

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
                detail = _api_detail(r)
                st.error(f"Errore: {detail}")

# ── OPPORTUNITY ────────────────────────────────────────────────────────────────
def show_opportunity(groups):
    st.markdown('<p class="main-title">🎯 Opportunity</p>', unsafe_allow_html=True)
    st.markdown("---")

    tab_labels = ["📋 Lista", "➕ Nuova Opportunity"] if can_write(groups) else ["📋 Lista"]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        resp      = api("GET", "/opportunities/")
        mans_resp = api("GET", "/mansioni/")
        res_resp  = api("GET", "/resources/")
        mr_resp   = api("GET", "/match/all/results") if False else None  # placeholder
        if not resp or resp.status_code != 200:
            st.error("Errore nel caricamento opportunity.")
            return
        opportunities  = resp.json()
        mans_map       = {m["id"]: m["nome"] for m in (mans_resp.json() if mans_resp and mans_resp.status_code == 200 else [])}
        res_name_map   = {r["id"]: f"{r.get('nome','')} {r.get('cognome','')}" for r in (res_resp.json() if res_resp and res_resp.status_code == 200 else [])}
        if not opportunities:
            st.info("Nessuna opportunity presente.")

        current_uid = (st.session_state.user or {}).get("id", "")

        for o in opportunities:
            stato = o.get("stato","")
            icon  = "🟢" if stato == "New" else ("🔵" if stato == "Active" else ("🟡" if stato == "Pending" else "🔴"))
            is_owner = o.get("manager_id") == current_uid or is_admin(groups)

            # carica risultati matching per questa opportunity (solo se esistono)
            slots = o.get("slot_risorse", [])
            confirmed_per_slot = {}  # slot_index → (risorsa_id, risorsa_nome)
            mr = api("GET", f"/match/{o['id']}/results")
            if mr and mr.status_code == 200:
                for sl_data in mr.json().get("slots", []):
                    for cand in sl_data.get("candidates", []):
                        if cand.get("stato") == "Confirmed":
                            sidx = sl_data["slot_index"]
                            confirmed_per_slot[sidx] = cand.get("risorsa_nome", "?")
                            break

            n_confirmed  = len(confirmed_per_slot)
            n_slots_tot  = len(slots)
            match_badge  = f"  ✅ {n_confirmed}/{n_slots_tot} slot confermati" if confirmed_per_slot else ""

            with st.expander(f"{icon} **{o.get('titolo','')}** — {o.get('cliente','')}  [{stato}]{match_badge}"):
                # ── dettaglio ──
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Inizio:** {o.get('data_inizio','')}")
                    st.markdown(f"**Fine prevista:** {o.get('data_fine_prevista','')}")
                    st.markdown(f"**Risorse richieste:** {n_slots_tot}")
                    for idx, sl in enumerate(slots, 1):
                        mn      = mans_map.get(sl.get("mansione_id",""), sl.get("mansione_id",""))
                        conf_nm = confirmed_per_slot.get(idx - 1)
                        slot_lbl = f"  Slot {idx}: {mn} — {sl.get('percentuale_allocazione','')}%"
                        if conf_nm:
                            st.caption(f"{slot_lbl}  ✅ *{conf_nm}*")
                        else:
                            st.caption(slot_lbl)
                with c2:
                    for s in o.get("skill_richieste", []):
                        st.markdown(f"  • `{s.get('skill_id','')}` lv.{s.get('livello_minimo','')}")
                    desc = o.get("descrizione","")
                    if desc:
                        st.caption(desc[:160])

                # ── azioni ──
                if can_write(groups):
                    action_cols = st.columns(4)
                    with action_cols[0]:
                        if stato == "New" and st.button("🤖 Matching AI", key=f"goto_match_{o['id']}"):
                            st.session_state.match_opp_id = o["id"]
                            st.session_state.page = "matching"
                            st.rerun()
                    with action_cols[1]:
                        if stato in ("New", "Active"):
                            if st.button("📤 Richiedi Promozione", key=f"promo_{o['id']}"):
                                r = api("POST", f"/promotions/request/{o['id']}")
                                if r and r.status_code == 201:
                                    st.success("✅ Richiesta inviata!")
                                    st.rerun()
                                else:
                                    detail = _api_detail(r)
                                    st.error(f"Errore: {detail}")
                        elif stato == "Pending":
                            st.info("⏳ Approvazione in corso")
                    with action_cols[2]:
                        if is_owner and stato in ("New", "Active"):
                            if st.button("✏️ Modifica", key=f"edit_opp_{o['id']}"):
                                st.session_state[f"editing_opp_{o['id']}"] = True
                                st.rerun()
                    with action_cols[3]:
                        if is_owner and stato == "New":
                            if st.button("🗑️ Elimina", key=f"del_opp_{o['id']}"):
                                st.session_state[f"confirm_del_opp_{o['id']}"] = True
                                st.rerun()

                    # ── form eliminazione ──
                    if st.session_state.get(f"confirm_del_opp_{o['id']}"):
                        st.warning("Confermi l'eliminazione di questa opportunity?")
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button("Sì, elimina", key=f"yes_del_{o['id']}", type="primary"):
                                r = api("DELETE", f"/opportunities/{o['id']}")
                                if r and r.status_code == 204:
                                    st.session_state.pop(f"confirm_del_opp_{o['id']}", None)
                                    st.rerun()
                                else:
                                    detail = _api_detail(r)
                                    st.error(f"Errore: {detail}")
                        with cc2:
                            if st.button("Annulla", key=f"no_del_{o['id']}"):
                                st.session_state.pop(f"confirm_del_opp_{o['id']}", None)
                                st.rerun()

                    # ── form modifica ──
                    if st.session_state.get(f"editing_opp_{o['id']}"):
                        st.markdown("#### ✏️ Modifica Opportunity")
                        skills_r  = api("GET", "/skills/")
                        mans_r2   = api("GET", "/mansioni/")
                        skills    = skills_r.json() if skills_r and skills_r.status_code == 200 else []
                        mansioni  = mans_r2.json() if mans_r2 and mans_r2.status_code == 200 else []
                        skill_map = {s["nome"]: s["id"] for s in skills}
                        skill_id_to_nome = {s["id"]: s["nome"] for s in skills}
                        mans_options = [m["nome"] for m in mansioni]
                        mans_id_map  = {m["nome"]: m["id"] for m in mansioni}

                        cur_slots = o.get("slot_risorse", [])
                        nslots_key = f"edit_nslots_{o['id']}"
                        if nslots_key not in st.session_state:
                            st.session_state[nslots_key] = len(cur_slots) or 1
                        n_edit_slots = st.number_input(
                            "Numero di risorse (slot)", 1, 10,
                            key=nslots_key
                        )

                        with st.form(f"form_edit_opp_{o['id']}"):
                            ec1, ec2 = st.columns(2)
                            with ec1:
                                new_titolo  = st.text_input("Titolo", value=o.get("titolo",""))
                                new_cliente = st.text_input("Cliente", value=o.get("cliente",""))
                                new_inizio  = st.text_input("Data inizio (YYYY-MM-DD)", value=o.get("data_inizio",""))
                            with ec2:
                                new_fine    = st.text_input("Data fine (YYYY-MM-DD)", value=o.get("data_fine_prevista",""))

                            st.markdown("**Composizione team richiesto:**")
                            for si in range(int(n_edit_slots)):
                                sc1, sc2 = st.columns(2)
                                prev_slot = cur_slots[si] if si < len(cur_slots) else {}
                                prev_mans = mans_map.get(prev_slot.get("mansione_id",""), mans_options[0] if mans_options else "")
                                prev_perc = prev_slot.get("percentuale_allocazione", 100)
                                with sc1:
                                    m_idx = mans_options.index(prev_mans) if prev_mans in mans_options else 0
                                    st.selectbox(f"Mansione — Risorsa {si+1}", mans_options, index=m_idx, key=f"eopp_m_{o['id']}_{si}")
                                with sc2:
                                    st.slider(f"Allocazione % — Risorsa {si+1}", 10, 100, int(prev_perc), 10, key=f"eopp_p_{o['id']}_{si}")

                            cur_skills = [skill_id_to_nome.get(s.get("skill_id",""), s.get("skill_id",""))
                                          for s in o.get("skill_richieste",[])]
                            new_skills = st.multiselect("Skills richieste", list(skill_map.keys()), default=[s for s in cur_skills if s in skill_map])
                            new_lv     = st.slider("Livello minimo skills", 1, 5, 3)
                            new_desc   = st.text_area("Descrizione", value=o.get("descrizione",""))

                            c_save, c_cancel = st.columns(2)
                            with c_save:
                                save = st.form_submit_button("💾 Salva", type="primary", use_container_width=True)
                            with c_cancel:
                                cancel = st.form_submit_button("Annulla", use_container_width=True)

                            if save:
                                new_slots = [
                                    {
                                        "mansione_id": mans_id_map.get(st.session_state.get(f"eopp_m_{o['id']}_{si}", mans_options[0] if mans_options else ""), ""),
                                        "percentuale_allocazione": st.session_state.get(f"eopp_p_{o['id']}_{si}", 100),
                                    }
                                    for si in range(int(n_edit_slots))
                                ]
                                payload = {
                                    "titolo": new_titolo, "cliente": new_cliente,
                                    "data_inizio": new_inizio, "data_fine_prevista": new_fine,
                                    "descrizione": new_desc,
                                    "skill_richieste": [{"skill_id": skill_map[s], "livello_minimo": new_lv} for s in new_skills],
                                    "slot_risorse": new_slots,
                                }
                                r = api("PATCH", f"/opportunities/{o['id']}", json=payload)
                                if r and r.status_code == 200:
                                    st.session_state.pop(f"editing_opp_{o['id']}", None)
                                    st.session_state.pop(nslots_key, None)
                                    st.rerun()
                                else:
                                    detail = _api_detail(r)
                                    st.error(f"Errore: {detail}")
                            if cancel:
                                st.session_state.pop(f"editing_opp_{o['id']}", None)
                                st.session_state.pop(nslots_key, None)
                                st.rerun()

    if can_write(groups) and len(tabs) > 1:
        with tabs[1]:
            _form_crea_opportunity()

def _form_crea_opportunity():
    skills_r  = api("GET", "/skills/")
    mans_r    = api("GET", "/mansioni/")
    skills    = skills_r.json() if skills_r and skills_r.status_code == 200 else []
    mansioni  = mans_r.json()   if mans_r   and mans_r.status_code   == 200 else []
    skill_map = {s["nome"]: s["id"] for s in skills}
    mans_options = [m["nome"] for m in mansioni]
    mans_id_map  = {m["nome"]: m["id"] for m in mansioni}
    manager_id   = (st.session_state.user or {}).get("id", "")

    import datetime as _dt2

    n_slots = st.number_input(
        "Numero di risorse necessarie", 1, 10, 1, key="nopp_nslots",
        help="Definisce quanti slot/ruoli servono per questa opportunity"
    )

    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Titolo *",                  key="nopp_titolo")
        st.text_input("Cliente *",                 key="nopp_cliente")
        st.text_input("Referente — Nome",          key="nopp_ref_nome")
        st.date_input("Data inizio",               key="nopp_data_inizio")
    with c2:
        st.text_input("Referente — Cognome",       key="nopp_ref_cognome")
        st.date_input("Data fine prevista",        key="nopp_data_fine")

    st.markdown("**Composizione team richiesto:**")
    for si in range(int(n_slots)):
        sc1, sc2 = st.columns(2)
        with sc1:
            st.selectbox(f"Mansione — Risorsa {si+1}", mans_options, key=f"nopp_slot_m_{si}")
        with sc2:
            st.slider(f"Allocazione % — Risorsa {si+1}", 10, 100, 100, 10, key=f"nopp_slot_p_{si}")

    st.multiselect("Skills richieste *", list(skill_map.keys()), key="nopp_skills")
    st.slider("Livello minimo skills (1–5)", 1, 5, 3, key="nopp_lv_min")
    st.text_area("Descrizione", key="nopp_descrizione")

    if st.button("✅ Crea Opportunity", type="primary", use_container_width=True, key="nopp_submit"):
        titolo_v   = (st.session_state.get("nopp_titolo") or "").strip()
        cliente_v  = (st.session_state.get("nopp_cliente") or "").strip()
        skills_v   = st.session_state.get("nopp_skills") or []
        if not all([titolo_v, cliente_v, skills_v]):
            st.error("Compila i campi obbligatori (*): Titolo, Cliente e almeno una Skill.")
            return
        slot_risorse = [
            {
                "mansione_id": mans_id_map.get(st.session_state.get(f"nopp_slot_m_{si}", mans_options[0] if mans_options else ""), ""),
                "percentuale_allocazione": st.session_state.get(f"nopp_slot_p_{si}", 100),
            }
            for si in range(int(n_slots))
        ]
        payload = {
            "titolo": titolo_v,
            "cliente": cliente_v,
            "referente_it_cliente": {
                "nome":    st.session_state.get("nopp_ref_nome", ""),
                "cognome": st.session_state.get("nopp_ref_cognome", ""),
            },
            "manager_id": manager_id,
            "skill_richieste": [{"skill_id": skill_map[s], "livello_minimo": st.session_state.get("nopp_lv_min", 3)}
                                 for s in skills_v],
            "slot_risorse": slot_risorse,
            "data_inizio":       str(st.session_state.get("nopp_data_inizio", _dt2.date.today())),
            "data_fine_prevista": str(st.session_state.get("nopp_data_fine",   _dt2.date.today())),
            "descrizione": st.session_state.get("nopp_descrizione", ""),
        }
        r = api("POST", "/opportunities/", json=payload)
        if r and r.status_code == 201:
            st.success("✅ Opportunity creata!")
            for k in [k2 for k2 in list(st.session_state.keys()) if k2.startswith("nopp_")]:
                del st.session_state[k]
            st.rerun()
        else:
            detail = _api_detail(r)
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
                    detail = _api_detail(r)
                    st.error(f"Errore: {detail}")

    st.markdown("---")
    st.markdown("### 📊 Shortlist per Slot")

    r_res = api("GET", f"/match/{sel_id}/results")
    if r_res is None:
        return
    if r_res.status_code == 404:
        st.info("Nessun risultato. Esegui prima il matching.")
        return
    if r_res.status_code != 200:
        st.error("Errore nel caricamento risultati.")
        return

    data  = r_res.json()
    slots = data.get("slots", [])

    if not slots:
        st.info("Nessun risultato disponibile.")
        return

    for slot in slots:
        sidx    = slot["slot_index"]
        mn      = slot.get("mansione_nome","")
        perc    = slot.get("percentuale_allocazione","")
        cands   = slot.get("candidates", [])
        n_confirmed = sum(1 for c in cands if c.get("stato") == "Confirmed")

        st.markdown(f"#### Slot {sidx+1} — {mn} @ {perc}%"
                    + (f"  ✅ *({n_confirmed} confermato/i)*" if n_confirmed else ""))

        if not cands:
            st.caption("Nessun candidato trovato per questo slot.")
            continue

        for i, item in enumerate(cands, 1):
            score  = item.get("score", 0)
            stato  = item.get("stato", "Proposed")
            nome   = item.get("risorsa_nome", "")
            motiv  = item.get("motivazione", "")
            disp   = item.get("disponibilita", 0)
            rid    = item.get("id","")
            ruolo_n = item.get("ruolo_nome","")
            senio   = item.get("seniority","")

            score_color = "🟢" if score >= 80 else ("🟡" if score >= 60 else "🔴")
            status_icon = {"Confirmed": "✅", "Rejected": "❌", "Proposed": "⏳"}.get(stato, "⏳")

            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                with c1:
                    st.markdown(f"**{i}. {nome}**")
                    if ruolo_n:
                        st.caption(f"🏷 {ruolo_n}" + (f" · {senio}" if senio else ""))
                    st.caption(motiv[:120] + "…" if len(motiv) > 120 else motiv)
                with c2:
                    st.markdown(f"{score_color} **{score}/100**")
                    st.progress(score / 100)
                with c3:
                    st.markdown(f"Disponibilità: **{int(disp)}%**")
                    st.markdown(f"{status_icon} {stato}")
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
                    elif stato == "Confirmed" and can_write(groups):
                        if st.button("↩️", key=f"undo_{rid}", help="Riporta a Proposed"):
                            api("PATCH", f"/match/{sel_id}/results/{rid}",
                                params={"stato": "Proposed"})
                            st.rerun()
        st.markdown("---")

# ── APPROVAZIONI ──────────────────────────────────────────────────────────────
def show_approvazioni(groups):
    st.markdown('<p class="main-title">📋 Approvazioni Promozione</p>', unsafe_allow_html=True)
    st.caption("Richieste di promozione Opportunity → Progetto Attivo")
    st.markdown("---")

    tab_pending, tab_history = st.tabs(["⏳ In Attesa", "📜 Storico"])

    with tab_pending:
        r = api("GET", "/promotions/pending")  # noqa: E501
        if not r or r.status_code != 200:
            st.error("Errore nel caricamento richieste.")
            return
        pending = r.json()

        if not pending:
            st.info("Nessuna richiesta in attesa.")
        else:
            for req in pending:
                opp = req.get("opportunity", {})
                with st.container(border=True):
                    st.markdown(f"### 🎯 {req.get('opportunity_titolo','')} — {req.get('opportunity_cliente','')}")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Richiesta da:** {req.get('requested_by_nome','')}")
                        st.markdown(f"**Data richiesta:** {req.get('requested_at','')[:10]}")
                        note = req.get("note_manager","")
                        if note:
                            st.markdown(f"**Note Manager:** {note}")
                    with c2:
                        st.markdown("**Risorse confermate per slot:**")
                        for sd in req.get("slots_dettaglio", []):
                            st.markdown(f"  • Slot {sd['slot_index']+1}: {sd.get('nome','')} — **{sd.get('percentuale_allocazione','')}%**")

                    st.markdown("---")
                    note_col, btn_col = st.columns([3, 2])
                    with note_col:
                        nota_exec = st.text_input("Note Executive (opzionale)",
                                                  key=f"nota_{req['id']}", label_visibility="collapsed",
                                                  placeholder="Note Executive (opzionale)")
                    with btn_col:
                        col_ok, col_no = st.columns(2)
                        with col_ok:
                            if st.button("✅ Approva", key=f"appr_{req['id']}", type="primary"):
                                rv = api("PATCH", f"/promotions/{req['id']}/review",
                                         params={"decision": "Approved", "note_executive": nota_exec})
                                if rv and rv.status_code == 200:
                                    st.success("✅ Opportunity promossa a Progetto Attivo!")
                                    st.rerun()
                                else:
                                    detail = _api_detail(rv)
                                    st.error(f"Errore: {detail}")
                        with col_no:
                            if st.button("❌ Rifiuta", key=f"rif_{req['id']}"):
                                rv = api("PATCH", f"/promotions/{req['id']}/review",
                                         params={"decision": "Rejected", "note_executive": nota_exec})
                                if rv and rv.status_code == 200:
                                    st.warning("Richiesta rifiutata — Opportunity riportata in stato New.")
                                    st.rerun()
                                else:
                                    detail = _api_detail(rv)
                                    st.error(f"Errore: {detail}")

    with tab_history:
        r2 = api("GET", "/promotions/")
        if r2 and r2.status_code == 200:
            all_reqs = [x for x in r2.json() if x.get("stato") != "Pending"]
            if not all_reqs:
                st.info("Nessuna richiesta elaborata.")
            for req in reversed(all_reqs):
                icon = "✅" if req.get("stato") == "Approved" else "❌"
                st.markdown(f"{icon} **{req.get('opportunity_titolo','')}** — "
                            f"{req.get('stato','')} il {(req.get('reviewed_at') or '')[:10]}")

    # ── TAB: modifiche progetto ──
    st.markdown("---")
    st.markdown("### 🔧 Richieste Modifica Progetto")
    rpc = api("GET", "/project-changes/pending")
    if rpc and rpc.status_code == 200:
        pcr_list = rpc.json()
        if not pcr_list:
            st.info("Nessuna richiesta di modifica progetto in attesa.")
        for req in pcr_list:
            ct = req.get("change_type","")
            ct_label = {"update_info":"✏️ Modifica info","add_resource":"➕ Aggiungi risorsa","remove_resource":"🔓 Rilascia risorsa"}.get(ct, ct)
            with st.container(border=True):
                st.markdown(f"### {ct_label} — **{req.get('project_nome','')}** ({req.get('project_cliente','')})")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Richiesto da:** {req.get('requested_by_nome','')}")
                    st.markdown(f"**Data:** {req.get('requested_at','')[:10]}")
                    if req.get("note_manager"):
                        st.markdown(f"**Note:** {req['note_manager']}")
                with c2:
                    if ct == "update_info":
                        pl = req.get("payload",{})
                        for k,v in pl.items():
                            st.markdown(f"  • `{k}`: {v}")
                    elif ct in ("add_resource","remove_resource"):
                        r_nome = req.get("risorsa_nome","")
                        alloc  = req.get("allocazione",{})
                        pl     = req.get("payload",{})
                        st.markdown(f"**Risorsa:** {r_nome}")
                        if ct == "add_resource":
                            st.markdown(f"**Allocazione:** {pl.get('percentuale','')}%  —  {pl.get('ruolo_nel_progetto','')}")
                        elif ct == "remove_resource" and alloc:
                            st.markdown(f"**Allocazione attuale:** {alloc.get('percentuale','')}%")

                st.markdown("---")
                note_col2, btn_col2 = st.columns([3,2])
                with note_col2:
                    nota_e2 = st.text_input("Note Executive", key=f"nota_pcr_{req['id']}",
                                            label_visibility="collapsed", placeholder="Note Executive (opzionale)")
                with btn_col2:
                    col_ok2, col_no2 = st.columns(2)
                    with col_ok2:
                        if st.button("✅ Approva", key=f"appr_pcr_{req['id']}", type="primary"):
                            rv = api("PATCH", f"/project-changes/{req['id']}/review",
                                     params={"decision":"Approved","note_executive":nota_e2})
                            if rv and rv.status_code == 200:
                                st.success("✅ Modifica applicata!")
                                st.rerun()
                            else:
                                detail = _api_detail(rv)
                                st.error(f"Errore: {detail}")
                    with col_no2:
                        if st.button("❌ Rifiuta", key=f"rif_pcr_{req['id']}"):
                            rv = api("PATCH", f"/project-changes/{req['id']}/review",
                                     params={"decision":"Rejected","note_executive":nota_e2})
                            if rv and rv.status_code == 200:
                                st.warning("Richiesta rifiutata.")
                                st.rerun()
                            else:
                                detail = _api_detail(rv)
                                st.error(f"Errore: {detail}")


def _form_modifica_dipendente():
    st.markdown("### ✏️ Modifica Dipendente")

    res_r = api("GET", "/resources/")
    resources = res_r.json() if res_r and res_r.status_code == 200 else []
    if not resources:
        st.info("Nessuna risorsa disponibile.")
        return

    res_opts = {f"{r['nome']} {r['cognome']} — {r.get('ruolo_nome','')}": r["id"] for r in sorted(resources, key=lambda r: r.get("ruolo_nome",""))}
    sel_label = st.selectbox("Seleziona dipendente da modificare", list(res_opts.keys()), key="edit_dip_sel")
    sel_id    = res_opts[sel_label]
    sel_res   = next(r for r in resources if r["id"] == sel_id)

    mansioni_r = api("GET", "/mansioni/")
    skills_r   = api("GET", "/skills/")
    groups_r   = api("GET", "/roles/")

    mansioni  = mansioni_r.json() if mansioni_r and mansioni_r.status_code == 200 else []
    skills    = skills_r.json()   if skills_r   and skills_r.status_code   == 200 else []
    rgroups   = groups_r.json()   if groups_r   and groups_r.status_code   == 200 else []

    mansione_map = {m["nome"]: m["id"] for m in mansioni}
    mansione_id_map = {m["id"]: m["nome"] for m in mansioni}
    skill_map    = {s["nome"]: s["id"] for s in skills}
    skill_id_map = {s["id"]: s["nome"] for s in skills}
    group_map    = {g["nome"]: g["id"] for g in rgroups}
    group_id_map = {g["id"]: g["nome"] for g in rgroups}

    import datetime as _dt

    cur_mansione = mansione_id_map.get(sel_res.get("ruolo_id",""), "")
    cur_skill_data = {
        skill_id_map.get(s.get("skill_id",""), s.get("skill_id","")): s.get("livello", 3)
        for s in sel_res.get("skill_ids", []) if isinstance(s, dict)
    }
    cur_skills   = list(cur_skill_data.keys())
    cur_groups   = [group_id_map.get(gid,"?") for gid in sel_res.get("gruppo_ruolo_ids",[])]
    cur_lingue   = [l.capitalize() for l in sel_res.get("lingue", [])]
    lingue_options = ["Italiano", "Inglese", "Tedesco", "Francese", "Spagnolo"]

    _raw_dn = sel_res.get("data_nascita","")
    try:
        _default_dn = _dt.date.fromisoformat(_raw_dn)
    except Exception:
        _default_dn = _dt.date(1990, 1, 1)

    # ── anagrafica + mansione + lingue + ruolo + costo (in form) ──────────────
    with st.form(f"form_edit_dip_{sel_id}", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            new_nome    = st.text_input("Nome *", value=sel_res.get("nome",""))
            new_email   = st.text_input("Email *", value=sel_res.get("email",""))
        with c2:
            new_cognome = st.text_input("Cognome *", value=sel_res.get("cognome",""))
            new_data_n  = st.date_input("Data di nascita", value=_default_dn,
                                        format="YYYY-MM-DD",
                                        min_value=_dt.date(1940, 1, 1))

        man_idx = list(mansione_map.keys()).index(cur_mansione) if cur_mansione in mansione_map else 0
        new_mansione = st.selectbox("Mansione", list(mansione_map.keys()), index=man_idx)
        new_lingue   = st.multiselect("Lingue", lingue_options,
                                      default=[l for l in cur_lingue if l in lingue_options])
        new_ruolo    = st.selectbox("Ruolo (autorizzativo)", list(group_map.keys()),
                                    index=list(group_map.keys()).index(cur_groups[0]) if cur_groups and cur_groups[0] in group_map else 0)
        new_costo    = st.number_input("Costo orario €/h", 0.0, 500.0,
                                       float(sel_res.get("costo_orario", 0.0)))
        save = st.form_submit_button("💾 Salva Modifiche", type="primary", use_container_width=True)

    # ── skills con livello per-skill (fuori dal form) ──────────────────────────
    st.markdown("**Skills assegnate:**")
    _sk_key = f"ed_skills_{sel_id}"
    if _sk_key not in st.session_state:
        st.session_state[_sk_key] = [s for s in cur_skills if s in skill_map]
    new_skills = st.multiselect("Seleziona skills", list(skill_map.keys()), key=_sk_key)
    if new_skills:
        st.markdown("**Livello per ogni skill:**")
        cols_sk = st.columns(min(len(new_skills), 3))
        for i, s in enumerate(new_skills):
            default_lv = cur_skill_data.get(s, 3)
            with cols_sk[i % 3]:
                st.slider(s, 1, 5, default_lv, key=f"ed_slv_{sel_id}_{s}",
                          help="1 = Base · 3 = Intermedio · 5 = Expert")

    # ── submit ─────────────────────────────────────────────────────────────────
    if save:
        if not all([new_nome, new_cognome, new_email]):
            st.error("Compila i campi obbligatori (*).")
        else:
            sel_skills_now = st.session_state.get(_sk_key, [])
            skill_ids = [{"skill_id": skill_map[s], "livello": st.session_state.get(f"ed_slv_{sel_id}_{s}", 3)}
                         for s in sel_skills_now if s in skill_map]
            payload = {
                "nome": new_nome, "cognome": new_cognome, "email": new_email,
                "data_nascita": str(new_data_n),
                "ruolo_id": mansione_map[new_mansione],
                "skill_ids": skill_ids,
                "lingue": [l.lower() for l in new_lingue],
                "gruppo_ruolo_ids": [group_map[new_ruolo]],
                "costo_orario": new_costo,
            }
            r = api("PUT", f"/resources/{sel_id}", json=payload)
            if r and r.status_code == 200:
                st.success("✅ Dipendente aggiornato!")
                st.session_state.pop(_sk_key, None)
            else:
                detail = _api_detail(r)
                st.error(f"Errore: {detail}")


# ── ADMIN ──────────────────────────────────────────────────────────────────────
def show_admin(groups):
    st.markdown('<p class="main-title">⚙️ Amministrazione</p>', unsafe_allow_html=True)
    st.markdown("---")

    tab_users, tab_groups, tab_skills, tab_new_dip, tab_edit_dip = st.tabs([
        "👥 Assegna Ruolo", "🔐 Ruoli Autorizzativi", "🛠 Skills",
        "👤 Nuovo Dipendente", "✏️ Modifica Dipendente"
    ])

    with tab_users:
        st.markdown("### Assegna Ruolo a una Risorsa")
        r_res = api("GET", "/resources/")
        r_grp = api("GET", "/roles/")
        resources   = r_res.json() if r_res and r_res.status_code == 200 else []
        role_groups = r_grp.json() if r_grp and r_grp.status_code == 200 else []
        grp_map     = {g["nome"]: g["id"] for g in role_groups}
        grp_id_map  = {g["id"]: g["nome"] for g in role_groups}

        # barre di ricerca
        sc1, sc2 = st.columns(2)
        with sc1:
            search_nome = st.text_input("🔍 Cerca per nome", key="admin_search_nome")
        with sc2:
            ruoli_presenti = sorted({r.get("ruolo_nome","") for r in resources if r.get("ruolo_nome","")})
            filter_ruolo   = st.selectbox("Filtra per mansione", ["— tutti —"] + ruoli_presenti, key="admin_filter_ruolo")

        # filtra
        filtered = resources
        if search_nome:
            filtered = [r for r in filtered
                        if search_nome.lower() in f"{r.get('nome','')} {r.get('cognome','')}".lower()]
        if filter_ruolo != "— tutti —":
            filtered = [r for r in filtered if r.get("ruolo_nome","") == filter_ruolo]

        # ordina per ruolo attuale
        filtered = sorted(filtered, key=lambda r: r.get("ruolo_nome",""))

        # etichetta con ruolo professionale e gruppo di accesso
        def _res_label(r):
            grp_names = ", ".join(grp_id_map.get(gid,"?") for gid in r.get("gruppo_ruolo_ids",[]))
            sen = r.get("seniority", "")
            mansione = r.get("ruolo_nome","")
            return f"{r['nome']} {r['cognome']}  |  👔 Mansione: {mansione} ({sen})  |  🔑 Ruolo: {grp_names}"

        res_labels = [_res_label(r) for r in filtered]
        res_ids    = [r["id"] for r in filtered]

        if not res_labels:
            st.info("Nessuna risorsa trovata con i filtri selezionati.")
        else:
            sel_idx  = st.selectbox("Risorsa", range(len(res_labels)),
                                    format_func=lambda i: res_labels[i],
                                    key="admin_sel_res")
            sel_res  = filtered[sel_idx]

            cur_grps = [grp_id_map.get(gid,"?") for gid in sel_res.get("gruppo_ruolo_ids",[])]
            st.caption(f"Ruolo attuale: **{', '.join(cur_grps) if cur_grps else 'nessuno'}**")

            sel_grps = st.multiselect("Nuovo Ruolo da assegnare", list(grp_map.keys()),
                                      default=[g for g in cur_grps if g in grp_map])

            if st.button("Aggiorna Gruppi", type="primary"):
                gids = [grp_map[g] for g in sel_grps]
                r    = api("PATCH", f"/roles/resources/{sel_res['id']}/groups", json=gids)
                if r and r.status_code == 200:
                    st.success("✅ Gruppi aggiornati!")
                    st.session_state.pop("cached_groups", None)
                else:
                    detail = _api_detail(r)
                    st.error(f"Errore: {detail}")

    with tab_groups:
        st.markdown("### Ruoli Autorizzativi — Permessi e Utenti Assegnati")

        PERMESSI = {
            "Employee": [
                "👁 Visualizza risorse, progetti, opportunity",
                "👁 Visualizza risultati matching AI",
            ],
            "Manager": [
                "✅ Tutto ciò che può fare Employee",
                "➕ Crea e modifica le proprie opportunity",
                "🤖 Lancia il Matching AI",
                "✔️ Conferma/rifiuta risorse dalla shortlist",
                "📤 Richiede promozione Opportunity → Progetto (approvazione Executive)",
                "🔧 Propone modifiche al proprio progetto (approvazione Executive)",
            ],
            "Executive": [
                "✅ Tutto ciò che può fare Manager",
                "📋 Approva o rifiuta promozioni Opportunity → Progetto",
                "📋 Approva o rifiuta modifiche ai progetti",
            ],
            "Administrator": [
                "✅ Tutto ciò che può fare Executive",
                "👤 Aggiunge e modifica dipendenti",
                "🛠 Aggiunge nuove skill",
                "🔑 Assegna ruoli autorizzativi alle risorse",
            ],
        }

        r_grp2 = api("GET", "/roles/")
        r_res  = api("GET", "/resources/?include_system=true")
        all_groups  = r_grp2.json() if r_grp2 and r_grp2.status_code == 200 else []
        all_res     = r_res.json()  if r_res  and r_res.status_code  == 200 else []

        grp_id_map2 = {g["id"]: g["nome"] for g in all_groups}

        _ROLE_ORDER = ["Employee", "Manager", "Executive", "Administrator"]
        for g in sorted(all_groups, key=lambda x: _ROLE_ORDER.index(x["nome"]) if x["nome"] in _ROLE_ORDER else 99):
            gname = g["nome"]
            utenti = [r for r in all_res if g["id"] in r.get("gruppo_ruolo_ids", [])]
            icon   = {"Employee":"🟢","Manager":"🔵","Executive":"🟣","Administrator":"🔴"}.get(gname,"⚪")

            with st.expander(f"{icon} **{gname}** — {len(utenti)} utenti assegnati"):
                col_perm, col_utenti = st.columns([3, 2])
                with col_perm:
                    st.markdown("**Permessi:**")
                    for p in PERMESSI.get(gname, ["(nessuna configurazione)"]):
                        st.markdown(f"  {p}")
                with col_utenti:
                    st.markdown("**Utenti assegnati:**")
                    if utenti:
                        for u in sorted(utenti, key=lambda x: x.get("cognome","")):
                            st.markdown(f"  • {u.get('nome','')} {u.get('cognome','')} — *{u.get('ruolo_nome','')}*")
                    else:
                        st.caption("Nessun utente assegnato")

    with tab_skills:
        st.markdown("### Skill Esistenti")
        sk_r = api("GET", "/skills/")
        skills_list = sk_r.json() if sk_r and sk_r.status_code == 200 else []
        funz = [s for s in skills_list if s.get("categoria") == "Funzionale"]
        tecn = [s for s in skills_list if s.get("categoria") == "Tecnica"]
        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown("**Funzionali**")
            for s in funz:
                st.markdown(f"  • `{s['id']}` {s['nome']}")
        with sc2:
            st.markdown("**Tecniche**")
            for s in tecn:
                st.markdown(f"  • `{s['id']}` {s['nome']}")

        st.markdown("### ➕ Aggiungi Skill")
        with st.form("form_skill"):
            sk_nome = st.text_input("Nome skill *")
            sk_cat  = st.selectbox("Categoria", ["Funzionale", "Tecnica"])
            sk_desc = st.text_input("Descrizione (opzionale)")
            if st.form_submit_button("✅ Crea Skill", type="primary"):
                if not sk_nome:
                    st.error("Il nome è obbligatorio.")
                else:
                    r = api("POST", "/skills/", json={"nome": sk_nome, "categoria": sk_cat, "descrizione": sk_desc})
                    if r and r.status_code == 201:
                        st.success(f"✅ Skill '{sk_nome}' creata!")
                        st.rerun()
                    else:
                        detail = _api_detail(r)
                        st.error(f"Errore: {detail}")

    with tab_new_dip:
        st.markdown("### ➕ Aggiungi Dipendente")
        _form_crea_risorsa()

    with tab_edit_dip:
        _form_modifica_dipendente()

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
    elif page == "approvazioni":
        show_approvazioni(groups)
    elif page == "admin":
        show_admin(groups)

main()
