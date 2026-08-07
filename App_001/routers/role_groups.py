from fastapi import APIRouter, HTTPException, Depends
from services import auth_service, db

router = APIRouter(prefix="/roles", tags=["Ruoli Autorizzativi"])

@router.get("/")
def list_role_groups(current_user: dict = Depends(auth_service.get_current_user)):
    return db.get_role_groups()

@router.patch("/{group_id}/roles")
def update_group_roles(
    group_id: str,
    ruoli_ids: list[str],
    current_user: dict = Depends(auth_service.is_admin),
):
    groups = db.get_role_groups()
    group = next((g for g in groups if g["id"] == group_id), None)
    if not group:
        raise HTTPException(status_code=404, detail="Gruppo non trovato")
    group["ruoli_ids"] = ruoli_ids
    db.save_role_groups(groups)
    return group

@router.patch("/resources/{resource_id}/groups")
def update_resource_groups(
    resource_id: str,
    gruppo_ruolo_ids: list[str],
    current_user: dict = Depends(auth_service.is_admin),
):
    resources = db.get_resources()
    resource = next((r for r in resources if r["id"] == resource_id), None)
    if not resource:
        raise HTTPException(status_code=404, detail="Risorsa non trovata")
    resource["gruppo_ruolo_ids"] = gruppo_ruolo_ids
    db.save_resources(resources)
    return {"id": resource_id, "gruppo_ruolo_ids": gruppo_ruolo_ids}
