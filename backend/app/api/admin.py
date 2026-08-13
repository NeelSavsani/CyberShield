from fastapi import APIRouter, Header, HTTPException
from firebase_admin import auth, firestore
from app.services.firebase_admin import get_firebase_app

router = APIRouter(prefix="/admin", tags=["Admin"])

def _admin_request(authorization: str | None):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Firebase authorization is required.")
    try:
        get_firebase_app()
        decoded = auth.verify_id_token(authorization.split(" ", 1)[1])
    except Exception as error:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase token: {error}") from error
    if decoded.get("admin") is not True:
        raise HTTPException(status_code=403, detail="Administrator permission is required.")
    return decoded

@router.patch("/users/{uid}/role")
def update_user_role(uid: str, role: str, authorization: str | None = Header(default=None)):
    caller = _admin_request(authorization)
    if uid == caller.get("uid") and role != "admin":
        raise HTTPException(status_code=400, detail="You cannot remove your own admin role.")
    if role not in {"admin", "user"}:
        raise HTTPException(status_code=400, detail="Role must be admin or user.")
    get_firebase_app()
    target = auth.get_user(uid)
    claims = dict(target.custom_claims or {})
    if role == "admin": claims["admin"] = True
    else: claims.pop("admin", None)
    auth.set_custom_user_claims(uid, claims)
    # Keep a display-only role mirror for the admin table. Authorization still
    # comes from the custom claim and Firestore rules, never this field.
    firestore.client().collection("users").document(uid).set({"role": role}, merge=True)
    return {"success": True, "uid": uid, "role": role}
