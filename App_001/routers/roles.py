from fastapi import APIRouter, Depends
from services import auth_service, db

router = APIRouter(prefix="/roles", tags=["Ruoli"])

@router.get("/")
def list_roles(current_user: dict = Depends(auth_service.get_current_user)):
    return db.get_roles()
