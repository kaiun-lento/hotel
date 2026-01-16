from __future__ import annotations

import sys

from sqlalchemy import text

from app.db.base import Base
from app.db.session import engine, SessionLocal

# Import models to register with SQLAlchemy
import app.models  # noqa: F401


DEFAULT_PERMISSIONS = [
    # Audit
    {"code": "AUDIT_VIEW", "category": "audit", "description": "View audit logs and auth events"},
    # Settings
    {"code": "SETTINGS_MANAGE", "category": "settings", "description": "Update global settings"},
    # Venue
    {"code": "VENUE_MANAGE", "category": "venue", "description": "Create/update venues"},
    # Reservations
    {"code": "RESERVATION_VIEW", "category": "reservation", "description": "View reservations"},
    {"code": "RESERVATION_EDIT", "category": "reservation", "description": "Edit reservations"},
    {"code": "RESERVATION_CANCEL", "category": "reservation", "description": "Cancel reservations"},
    # Rules / blocks
    {"code": "RULES_VIEW", "category": "rules", "description": "View booking rules and calendar blocks"},
    {"code": "RULES_MANAGE", "category": "rules", "description": "Manage booking rules"},
    {"code": "CALENDAR_BLOCK_SINGLE", "category": "rules", "description": "Create/delete single calendar blocks"},
    {"code": "CALENDAR_BLOCK_BULK", "category": "rules", "description": "Create calendar blocks in bulk"},
    # Menu
    {"code": "MENU_MANAGE", "category": "menu", "description": "Manage menu categories/items/photos"},
    # Layout
    {"code": "LAYOUT_MANAGE", "category": "layout", "description": "Manage venue layout templates and assets"},
    # Printing
    {"code": "PRINT_DAILY", "category": "print", "description": "Print daily reservation list"},
    {"code": "PRINT_MONTHLY", "category": "print", "description": "Print monthly reservation view"},
]


def main() -> int:
    # Extensions needed for exclusion constraints (overlap prevention)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Add exclusion constraint to prevent overlapping reservations per venue
    with engine.begin() as conn:
        try:
            conn.execute(
                text(
                    """
                    ALTER TABLE reservations
                    ADD CONSTRAINT reservations_no_overlap
                    EXCLUDE USING gist (
                        venue_id WITH =,
                        tstzrange(start_at, end_at, '[)') WITH &&
                    )
                    WHERE (status <> 'CANCELLED');
                    """
                )
            )
        except Exception:
            # likely already exists
            pass

    # Seed permissions and default settings row
    from app.models.permission import Permission
    from app.models.settings import AppSettings

    db = SessionLocal()
    try:
        for p in DEFAULT_PERMISSIONS:
            existing = db.get(Permission, p["code"])
            if existing is None:
                db.add(Permission(code=p["code"], category=p["category"], description=p["description"]))

        if db.get(AppSettings, 1) is None:
            db.add(AppSettings(id=1))

        db.commit()
    finally:
        db.close()

    print("DB initialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
