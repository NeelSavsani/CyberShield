from fastapi import APIRouter, Header, HTTPException
from firebase_admin import auth, firestore
from app.services.firebase_admin import get_firebase_app

router = APIRouter(prefix="/admin", tags=["Admin"])


def _as_json_value(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value

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


@router.get("/users")
def list_admin_users(authorization: str | None = Header(default=None)):
    """Return one consistent user list using Firebase Auth claims as authority."""
    _admin_request(authorization)
    get_firebase_app()
    client = firestore.client()
    firestore_users = {
        doc.id: doc.to_dict() for doc in client.collection("users").stream()
    }

    try:
        records = list(auth.list_users().iterate_all())
    except Exception as error:
        raise HTTPException(
            status_code=502, detail=f"Unable to load Firebase users: {error}"
        ) from error

    users = []
    for record in records:
        data = firestore_users.get(record.uid, {})
        claims = record.custom_claims or {}
        role = "admin" if claims.get("admin") is True else "user"

        # Keep the profile mirror in sync, but never use it for authorization.
        if data.get("role") != role:
            client.collection("users").document(record.uid).set(
                {"role": role}, merge=True
            )

        first_name = data.get("firstName") or data.get("first_name") or ""
        last_name = data.get("lastName") or data.get("last_name") or ""
        email = record.email or data.get("email") or ""
        display_name = (
            data.get("displayName")
            or data.get("display_name")
            or data.get("name")
            or record.display_name
            or " ".join(filter(None, [first_name, last_name]))
            or email.split("@", 1)[0]
            or "User"
        )
        metadata = record.user_metadata
        created_at = (
            getattr(metadata, "creation_timestamp", None)
            or data.get("createdAt")
            or data.get("joined")
        )
        last_login = (
            getattr(metadata, "last_sign_in_timestamp", None)
            or data.get("lastLogin")
        )
        users.append(
            {
                "id": record.uid,
                "uid": record.uid,
                "docId": record.uid,
                "email": email,
                "displayName": display_name,
                "name": display_name,
                "firstName": first_name,
                "lastName": last_name,
                "role": role,
                "status": "Disabled" if record.disabled else "Active",
                "createdAt": _as_json_value(created_at),
                "joined": _as_json_value(created_at),
                "lastLogin": _as_json_value(last_login),
                "photoURL": record.photo_url
                or data.get("photoURL")
                or data.get("photoUrl")
                or None,
            }
        )

    def sort_key(item):
        value = item.get("createdAt")
        if isinstance(value, (int, float)):
            return (1, value)
        return (0, str(value or ""))

    users.sort(key=sort_key, reverse=True)
    return users

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
