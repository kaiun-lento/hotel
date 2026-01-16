from __future__ import annotations

import argparse

from app.db.session import SessionLocal
from app.services.sheets_sync import export_reservations_to_sheet


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--service-account-json', required=True, help='Path to service account JSON')
    p.add_argument('--spreadsheet-id', required=True)
    p.add_argument('--worksheet', default='Reservations')
    p.add_argument('--mask-pii', action='store_true')
    args = p.parse_args()

    db = SessionLocal()
    try:
        n = export_reservations_to_sheet(
            db,
            service_account_json_path=args.service_account_json,
            spreadsheet_id=args.spreadsheet_id,
            worksheet_name=args.worksheet,
            mask_pii=args.mask_pii,
        )
        print(f'exported_rows={n}')
        return 0
    finally:
        db.close()


if __name__ == '__main__':
    raise SystemExit(main())
