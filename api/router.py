from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, public, admin_roles, admin_users, admin_audit, admin_settings, admin_venues, admin_rules, admin_blocks, admin_reservations, admin_prints, admin_menu, admin_layout

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(public.router, prefix="/public", tags=["public"])

# Admin
api_router.include_router(admin_roles.router, prefix="/admin/roles", tags=["admin-roles"])
api_router.include_router(admin_users.router, prefix="/admin/users", tags=["admin-users"])
api_router.include_router(admin_audit.router, prefix="/admin", tags=["admin-audit"])
api_router.include_router(admin_settings.router, prefix="/admin/settings", tags=["admin-settings"])
api_router.include_router(admin_venues.router, prefix="/admin/venues", tags=["admin-venues"])
api_router.include_router(admin_rules.router, prefix="/admin/booking-rules", tags=["admin-rules"])
api_router.include_router(admin_blocks.router, prefix="/admin/calendar-blocks", tags=["admin-blocks"])
api_router.include_router(admin_reservations.router, prefix="/admin/reservations", tags=["admin-reservations"])
api_router.include_router(admin_prints.router, prefix="/admin/prints", tags=["admin-prints"])

api_router.include_router(admin_menu.router, prefix="/admin/menu", tags=["admin-menu"])
api_router.include_router(admin_layout.router, prefix="/admin/layout", tags=["admin-layout"])
