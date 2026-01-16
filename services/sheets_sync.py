from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.customer import Customer
from app.models.reservation import Reservation
from app.models.venue import Venue


def _get_gspread_client(service_account_json_path: str):
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(service_account_json_path, scopes=scopes)
    return gspread.authorize(creds)


def export_reservations_to_sheet(
    db: Session,
    *,
    service_account_json_path: str,
    spreadsheet_id: str,
    worksheet_name: str = "Reservations",
    mask_pii: bool = False,
) -> int:
    """Export reservations to Google Sheets.

    - Writes a single table into `worksheet_name`.
    - Returns number of rows written (excluding header).

    NOTE: This uses Google Sheets API credentials (service account).
    """

    settings = get_settings()
    tz = ZoneInfo(settings.timezone)

    client = _get_gspread_client(service_account_json_path)
    sh = client.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(worksheet_name)
    except Exception:
        ws = sh.add_worksheet(title=worksheet_name, rows="1000", cols="20")

    reservations = db.execute(select(Reservation).order_by(Reservation.start_at.asc())).scalars().all()
    customer_ids = {r.customer_id for r in reservations}
    customers = {
        c.id: c
        for c in db.execute(select(Customer).where(Customer.id.in_(list(customer_ids)))).scalars().all()
    } if customer_ids else {}
    venues = {v.id: v for v in db.execute(select(Venue)).scalars().all()}

    header = [
        "public_id",
        "venue",
        "start_at",
        "end_at",
        "people_count",
        "booking_type",
        "banquet_name",
        "status",
        "customer_name",
        "phone",
        "email",
        "created_at",
        "updated_at",
    ]

    rows = [header]
    for r in reservations:
        cust = customers.get(r.customer_id)
        venue = venues.get(r.venue_id)
        start_local = r.start_at.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        end_local = r.end_at.astimezone(tz).strftime("%Y-%m-%d %H:%M")

        phone = cust.phone_masked if (mask_pii and cust) else (cust.phone_normalized if cust else "")
        email = cust.email_masked if (mask_pii and cust) else (cust.email_normalized if cust else "")

        rows.append(
            [
                r.public_id,
                venue.name if venue else r.venue_id,
                start_local,
                end_local,
                r.people_count,
                r.booking_type,
                r.banquet_name,
                r.status,
                cust.name if cust else "",
                phone,
                email,
                r.created_at.astimezone(tz).strftime("%Y-%m-%d %H:%M"),
                r.updated_at.astimezone(tz).strftime("%Y-%m-%d %H:%M"),
            ]
        )

    ws.clear()
    ws.update(rows)
    return len(rows) - 1
