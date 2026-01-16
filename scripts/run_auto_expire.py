from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.reservation import Reservation
from app.services.audit_service import write_audit_log
from app.services.settings_service import get_or_create_settings


def main() -> int:
    db = SessionLocal()
    try:
        s = get_or_create_settings(db)
        if not s.auto_expire_enabled:
            print("auto_expire_disabled")
            return 0

        cutoff = datetime.now(tz=ZoneInfo("UTC")) - timedelta(hours=s.auto_expire_hours)
        q = select(Reservation).where(Reservation.status == "PENDING", Reservation.created_at <= cutoff)
        targets = db.execute(q).scalars().all()

        if not targets:
            print("no_targets")
            return 0

        for r in targets:
            r.status = "CANCELLED"
            r.cancel_reason = "AUTO_EXPIRE"
            r.cancelled_at = datetime.now(tz=ZoneInfo("UTC"))
            db.commit()
            write_audit_log(
                db,
                actor_user_id=None,
                action_type="RESERVATION_AUTO_EXPIRE",
                target_type="reservation",
                target_id=r.public_id,
                summary="Auto-expired pending reservation",
                diff_json=None,
                request=None,
            )

        print(f"expired: {len(targets)}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
