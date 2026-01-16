from __future__ import annotations

import argparse

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User
from app.services.auth_service import normalize_email


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--password", required=True)

    args = parser.parse_args()

    email = normalize_email(args.email)

    db = SessionLocal()
    try:
        u = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if u is None:
            u = User(email=email, name=args.name, hashed_password=hash_password(args.password), is_active=True, is_root_admin=True)
            db.add(u)
            db.commit()
            print(f"Created root admin: {u.email}")
            return 0

        u.name = args.name
        u.hashed_password = hash_password(args.password)
        u.is_active = True
        u.is_root_admin = True
        db.commit()
        print(f"Updated root admin: {u.email}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
