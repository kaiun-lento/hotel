from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_db, require_permissions
from app.models.customer import Customer
from app.models.menu import MenuItem
from app.models.reservation import Reservation, ReservationMenuSelection
from app.models.venue import Venue
from app.services.audit_service import write_audit_log

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/daily", response_class=HTMLResponse)
def print_daily(
    request: Request,
    day: date = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user=Depends(require_permissions(["PRINT_DAILY"])),
):
    app_settings = get_settings()
    tz = ZoneInfo(app_settings.timezone)

    start_utc = datetime.combine(day, datetime.min.time()).replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
    end_utc = datetime.combine(day + timedelta(days=1), datetime.min.time()).replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))

    venues = db.execute(select(Venue).where(Venue.active == True).order_by(Venue.sort_order, Venue.name)).scalars().all()

    # Preload menu prices
    menu_map = {m.id: {"name": m.name, "price": int(m.price)} for m in db.execute(select(MenuItem)).scalars().all()}

    # Preload reservations
    reservations = db.execute(
        select(Reservation).where(
            Reservation.status != "CANCELLED",
            Reservation.start_at >= start_utc,
            Reservation.start_at < end_utc,
        )
    ).scalars().all()

    # Preload customers and menu selections
    customer_ids = {r.customer_id for r in reservations}
    customers = {
        c.id: c
        for c in db.execute(select(Customer).where(Customer.id.in_(list(customer_ids)))).scalars().all()
    } if customer_ids else {}

    res_ids = [r.id for r in reservations]
    selections = db.execute(select(ReservationMenuSelection).where(ReservationMenuSelection.reservation_id.in_(res_ids))).scalars().all() if res_ids else []

    sel_by_res: dict[str, list[ReservationMenuSelection]] = {}
    for s in selections:
        sel_by_res.setdefault(s.reservation_id, []).append(s)

    venue_rows = []
    for v in venues:
        vr = [r for r in reservations if r.venue_id == v.id]
        vr.sort(key=lambda x: x.start_at)

        rows = []
        for r in vr:
            local_start = r.start_at.astimezone(tz)
            local_end = r.end_at.astimezone(tz)
            time_range = f"{local_start.strftime('%H:%M')}-{local_end.strftime('%H:%M')}"

            cust = customers.get(r.customer_id)
            phone = cust.phone_normalized if cust else ""

            sels = sel_by_res.get(r.id, [])
            total = 0
            parts = []
            for s in sels:
                mi = menu_map.get(s.menu_item_id) or {}
                price = int(mi.get("price", 0))
                qty = int(s.quantity)
                total += price * qty
                parts.append(f"{mi.get('name', s.menu_item_id)} x{qty}")

            menu_summary = ", ".join(parts)
            rows.append(
                {
                    "banquet_name": r.banquet_name or "(未入力)",
                    "time_range": time_range,
                    "people_count": r.people_count,
                    "phone": phone,
                    "menu_summary": menu_summary,
                    "total_price": total,
                    "note": r.desired_time_text or "",
                }
            )

        venue_rows.append({"name": v.name, "reservations": rows})

    write_audit_log(
        db,
        actor_user_id=user.id,
        action_type="PRINT_DAILY",
        target_type="print",
        target_id=str(day),
        summary="Printed daily list",
        diff_json={"day": str(day)},
        request=request,
    )

    return templates.TemplateResponse(
        "daily_print.html",
        {
            "request": request,
            "date_str": day.isoformat(),
            "venues": venue_rows,
        },
    )


@router.get("/monthly")
def print_monthly_stub(
    month: str = Query(..., description="YYYY-MM"),
    user=Depends(require_permissions(["PRINT_MONTHLY"])),
):
    # As per your instruction, monthly print can be implemented later.
    return {"message": "Monthly print is planned (not implemented in MVP)", "month": month}
