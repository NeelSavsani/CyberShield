"""Grant the Firebase ``admin`` custom claim to one existing user.

Run this only from a trusted machine with a Firebase Admin SDK service-account
file. Never commit that credential or place it in the frontend.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import firebase_admin
from firebase_admin import auth, credentials


def main() -> None:
    parser = argparse.ArgumentParser(description="Grant the Firebase admin claim to a user")
    parser.add_argument("service_account", type=Path, help="Firebase service-account JSON path")
    parser.add_argument("email", help="Existing Firebase Authentication user email")
    args = parser.parse_args()

    if not args.service_account.is_file():
        raise SystemExit(f"Service-account file not found: {args.service_account}")

    firebase_admin.initialize_app(credentials.Certificate(str(args.service_account)))
    user = auth.get_user_by_email(args.email)
    claims = dict(user.custom_claims or {})
    claims["admin"] = True
    auth.set_custom_user_claims(user.uid, claims)
    print(f"Admin claim granted to {user.email} ({user.uid}).")
    print("Sign out and sign in again so the browser receives the new claim.")


if __name__ == "__main__":
    main()
