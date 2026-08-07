import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services import auth_service, db

router = APIRouter(prefix="/skills", tags=["Skill"])


class SkillCreate(BaseModel):
    nome: str
    categoria: str  # "Funzionale" | "Tecnica"
    descrizione: str = ""


@router.get("/")
def list_skills(current_user: dict = Depends(auth_service.get_current_user)):
    return db.get_skills()


@router.post("/", status_code=201)
def create_skill(
    body: SkillCreate,
    current_user: dict = Depends(auth_service.is_admin),
):
    if body.categoria not in ("Funzionale", "Tecnica"):
        raise HTTPException(status_code=400, detail="categoria deve essere 'Funzionale' o 'Tecnica'")
    skills = db.get_skills()
    if any(s["nome"].lower() == body.nome.lower() for s in skills):
        raise HTTPException(status_code=400, detail="Skill già esistente")
    new_id = f"SK{str(uuid.uuid4())[:3].upper()}{len(skills)+1:03d}"
    new_skill = {"id": new_id, "nome": body.nome, "categoria": body.categoria, "descrizione": body.descrizione}
    skills.append(new_skill)
    db.save_skills(skills)
    return new_skill
