from __future__ import annotations

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.customer import Customer
from app.models.reservation import Reservation
from app.models.venue import Venue
from app.services.auth_service import hash_pii, mask_email, mask_phone, normalize_email, normalize_phone

def _get_gspread_client(service_account_json_path: str):
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(service_account_json_path, scopes=scopes)
    return gspread.authorize(creds)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--service-account-json', required=True)
    p.add_argument('--spreadsheet-id', required=True)
    p.add_argument('--worksheet', default='Reservations')
    args = p.parse_args()

    settings = get_settings()
    tz = ZoneInfo(settings.timezone)

    client = _get_gspread_client(args.service_account_json)
    sh = client.open_by_key(args.spreadsheet_id)
    ws = sh.worksheet(args.worksheet)

    values = ws.get_all_values()
    if not values:
        print('no_data')
        return 0

    header = values[0]
    rows = values[1:]

    idx = {name: i for i, name in enumerate(header)}

    def get(row, key, default=''):
        return row[idx[key]] if key in idx and idx[key] < len(row) else default

    db = SessionLocal()
    created = 0
    updated = 0
    skipped = 0
    try:
        for row in rows:
            public_id = get(row, 'public_id', '').strip() or None
            venue_name = get(row, 'venue', '').strip()
            start_str = get(row, 'start_at', '').strip()
            end_str = get(row, 'end_at', '').strip()
            if not venue_name or not start_str or not end_str:
                skipped += 1
                continue

            try:
                start_local = datetime.strptime(start_str, '%Y-%m-%d %H:%M').replace(tzinfo=tz)
                end_local = datetime.strptime(end_str, '%Y-%m-%d %H:%M').replace(tzinfo=tz)
            except Exception:
                skipped += 1
                continue

            start_at = start_local.astimezone(ZoneInfo('UTC'))
            end_at = end_local.astimezone(ZoneInfo('UTC'))

            if start_at >= end_at:
                skipped += 1
                continue

            # Venue upsert
            venue = db.execute(select(Venue).where(Venue.name == venue_name)).scalar_one_or_none()
            if venue is None:
                venue = Venue(name=venue_name, sort_order=0, active=True)
                db.add(venue)
                db.commit()
                db.refresh(venue)

            # Customer upsert (by phone_hash if possible)
            name = get(row, 'customer_name', '').strip() or '(imported)'
            phone = normalize_phone(get(row, 'phone', '').strip())
            email = normalize_email(get(row, 'email', '').strip())
            phone_hash = hash_pii(phone) if phone else ''
            email_hash = hash_pii(email) if email else ''

            cust = None
            if phone_hash:
                cust = db.execute(select(Customer).where(Customer.phone_hash == phone_hash)).scalar_one_or_none()
            if cust is None and email_hash:
                cust = db.execute(select(Customer).where(Customer.email_hash == email_hash)).scalar_one_or_none()
            if cust is None:
                cust = Customer(
                    name=name,
                    phone_normalized=phone,
                    phone_hash=phone_hash,
                    phone_masked=mask_phone(phone),
                    email_normalized=email,
                    email_hash=email_hash,
                    email_masked=mask_email(email),
                    reservation_count=0,
                )
                db.add(cust)
                db.commit()
                db.refresh(cust)

            status = (get(row, 'status', '').strip() or 'PENDING')
            booking_type = (get(row, 'booking_type', '').strip() or 'BANQUET')
            people = int(get(row, 'people_count', '0') or 0)
            banquet_name = get(row, 'banquet_name', '').strip() or ''

            existing = None
            if public_id:
                existing = db.execute(select(Reservation).where(Reservation.public_id == public_id)).scalar_one_or_none()

            if existing is None:
                r = Reservation(
                    public_id=public_id or f'IMP-{venue.id[:6]}-{int(start_at.timestamp())}',
                    venue_id=venue.id,
                    customer_id=cust.id,
                    start_at=start_at,
                    end_at=end_at,
                    status=status,
                    booking_type=booking_type,
                    banquet_name=banquet_name,
                    people_count=people,
                )
                db.add(r)
                try:
                    db.commit()
                    created += 1
                except Exception:
                    db.rollback()
                    skipped += 1
            else:
                existing.venue_id = venue.id
                existing.customer_id = cust.id
                existing.start_at = start_at
                existing.end_at = end_at
                existing.status = status
                existing.booking_type = booking_type
                existing.banquet_name = banquet_name
                existing.people_count = people
                try:
                    db.commit()
                    updated += 1
                except Exception:
                    db.rollback()
                    skipped += 1

        print(f'created={created} updated={updated} skipped={skipped}')
        return 0
    finally:
        db.close()


if __name__ == '__main__':
    raise SystemExit(main())
