from fastapi import APIRouter, HTTPException, Depends
from models.schemas import LoginRequest, TokenResponse, ChangePasswordRequest
from services import auth_service, db

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user = auth_service.authenticate_user(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    role_groups = db.get_role_groups()
    gruppi = [g["nome"] for g in role_groups if g["id"] in user.get("gruppo_ruolo_ids", [])]
    token = auth_service.create_token({"sub": user["email"], "gruppi": gruppi})
    return TokenResponse(
        access_token=token,
        nome=user["nome"],
        cognome=user["cognome"],
        gruppi=gruppi,
    )

@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(auth_service.get_current_user),
):
    if not auth_service.authenticate_user(current_user["email"], body.password_attuale):
        raise HTTPException(status_code=400, detail="Password attuale non corretta")
    resources = db.get_resources()
    for r in resources:
        if r["id"] == current_user["id"]:
            r["password_hash"] = auth_service.hash_password(body.nuova_password)
            break
    db.save_resources(resources)
    return {"message": "Password aggiornata con successo"}

@router.get("/me")
def me(current_user: dict = Depends(auth_service.get_current_user)):
    role_groups = db.get_role_groups()
    roles = db.get_roles()
    gruppi = [g["nome"] for g in role_groups if g["id"] in current_user.get("gruppo_ruolo_ids", [])]
    ruolo = next((r for r in roles if r["id"] == current_user.get("ruolo_id")), {})
    return {
        "id": current_user["id"],
        "nome": current_user["nome"],
        "cognome": current_user["cognome"],
        "email": current_user["email"],
        "ruolo": ruolo.get("nome", ""),
        "gruppi": gruppi,
    }
