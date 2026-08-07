from fastapi import APIRouter, Depends
from services import auth_service, db

router = APIRouter(prefix="/skills", tags=["Skill"])

@router.get("/")
def list_skills(current_user: dict = Depends(auth_service.get_current_user)):
    return db.get_skills()
