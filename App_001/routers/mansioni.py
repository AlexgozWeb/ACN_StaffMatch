import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services import auth_service, db

router = APIRouter(prefix="/mansioni", tags=["Mansioni"])


class MansioneCreate(BaseModel):
    nome: str
    seniority: str
    descrizione: str = ""
    costo_orario: float = 0.0


@router.get("/")
def list_mansioni(current_user: dict = Depends(auth_service.get_current_user)):
    return db.get_roles()


@router.post("/", status_code=201)
def create_mansione(
    body: MansioneCreate,
    current_user: dict = Depends(auth_service.is_admin),
):
    mansioni = db.get_roles()
    if any(m["nome"].lower() == body.nome.lower() for m in mansioni):
        raise HTTPException(status_code=400, detail="Mansione già esistente")
    new_id = f"RU{len(mansioni)+1:03d}"
    new_m = {"id": new_id, "nome": body.nome, "seniority": body.seniority,
             "descrizione": body.descrizione, "costo_orario": body.costo_orario}
    mansioni.append(new_m)
    db.save_roles(mansioni)
    return new_m
