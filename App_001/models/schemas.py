from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum


class Categoria(str, Enum):
    funzionale = "Funzionale"
    tecnica = "Tecnica"

class Stato(str, Enum):
    new = "New"
    active = "Active"
    closed = "Closed"

class StatoMatch(str, Enum):
    proposed = "Proposed"
    confirmed = "Confirmed"
    rejected = "Rejected"

class StatoRichiesta(str, Enum):
    open = "Open"
    matched = "Matched"
    confirmed = "Confirmed"


class Skill(BaseModel):
    id: str
    nome: str
    categoria: Categoria
    descrizione: str

class Ruolo(BaseModel):
    id: str
    nome: str
    seniority: str
    descrizione: str
    costo_orario: float

class GruppoRuolo(BaseModel):
    id: str
    nome: str
    descrizione: str
    ruoli_ids: list[str]

class ResourceSkill(BaseModel):
    skill_id: str
    livello: int  # 1-5

class Risorsa(BaseModel):
    id: str
    nome: str
    cognome: str
    email: EmailStr
    data_nascita: str
    ruolo_id: str
    costo_orario: float
    skill_ids: list[ResourceSkill]
    lingue: list[str]
    is_active: bool
    gruppo_ruolo_ids: list[str]

class RisorsaCreate(BaseModel):
    nome: str
    cognome: str
    email: EmailStr
    data_nascita: str
    ruolo_id: str
    costo_orario: Optional[float] = None
    skill_ids: list[ResourceSkill] = []
    lingue: list[str] = []
    gruppo_ruolo_ids: list[str] = ["GR001"]

class ReferenteCliente(BaseModel):
    nome: str
    cognome: str

class Progetto(BaseModel):
    id: str
    nome: str
    cliente: str
    referente_it_cliente: ReferenteCliente
    manager_id: str
    skill_principale_id: str
    skill_secondarie_ids: list[str]
    data_inizio: str
    data_fine_prevista: str
    stato: Stato
    descrizione: str

class ProgettoCreate(BaseModel):
    nome: str
    cliente: str
    referente_it_cliente: ReferenteCliente
    manager_id: str
    skill_principale_id: str
    skill_secondarie_ids: list[str] = []
    data_inizio: str
    data_fine_prevista: str
    descrizione: str = ""

class SkillRichiesta(BaseModel):
    skill_id: str
    livello_minimo: int

class SlotRisorsa(BaseModel):
    mansione_id: str
    percentuale_allocazione: int  # 10–100

class Opportunity(BaseModel):
    id: str
    titolo: str
    cliente: str
    referente_it_cliente: ReferenteCliente
    manager_id: str
    skill_richieste: list[SkillRichiesta]
    slot_risorse: list[SlotRisorsa]
    data_inizio: str
    data_fine_prevista: str
    stato: Stato
    descrizione: str

class OpportunityCreate(BaseModel):
    titolo: str
    cliente: str
    referente_it_cliente: ReferenteCliente
    manager_id: str
    skill_richieste: list[SkillRichiesta]
    slot_risorse: list[SlotRisorsa]
    data_inizio: str
    data_fine_prevista: str
    descrizione: str = ""

class OpportunityUpdate(BaseModel):
    titolo: Optional[str] = None
    cliente: Optional[str] = None
    data_inizio: Optional[str] = None
    data_fine_prevista: Optional[str] = None
    descrizione: Optional[str] = None
    skill_richieste: Optional[list[SkillRichiesta]] = None
    slot_risorse: Optional[list[SlotRisorsa]] = None

class ProgettoUpdate(BaseModel):
    nome: Optional[str] = None
    cliente: Optional[str] = None
    data_fine_prevista: Optional[str] = None
    descrizione: Optional[str] = None

class AllocazioneCreate(BaseModel):
    risorsa_id: str
    percentuale: int
    data_inizio: str
    data_fine: str
    ruolo_nel_progetto: str = "Consultant"

class Allocazione(BaseModel):
    id: str
    risorsa_id: str
    progetto_id: str
    percentuale: int
    data_inizio: str
    data_fine: str
    ruolo_nel_progetto: str

class MatchResult(BaseModel):
    id: str
    opportunity_id: str
    risorsa_id: str
    score: int
    motivazione: str
    stato: StatoMatch

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    nome: str
    cognome: str
    gruppi: list[str]

class ChangePasswordRequest(BaseModel):
    password_attuale: str
    nuova_password: str
