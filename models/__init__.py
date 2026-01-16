# Import all models so that SQLAlchemy registers them for metadata.create_all
from app.models.permission import Permission
from app.models.role import Role, RolePermission
from app.models.user import User, UserRole
from app.models.login_challenge import LoginChallenge
from app.models.auth_event import AuthEvent
from app.models.audit_log import AuditLog
from app.models.venue import Venue
from app.models.customer import Customer
from app.models.menu import MenuCategory, MenuItem, MenuItemPhoto
from app.models.reservation import Reservation, ReservationMenuSelection
from app.models.booking_rule import BookingRule
from app.models.calendar_block import CalendarBlock
from app.models.settings import AppSettings
from app.models.reservation_token import ReservationAccessToken

__all__ = [
    "Permission",
    "Role",
    "RolePermission",
    "User",
    "UserRole",
    "LoginChallenge",
    "AuthEvent",
    "AuditLog",
    "Venue",
    "Customer",
    "MenuCategory",
    "MenuItem",
    "MenuItemPhoto",
    "Reservation",
    "ReservationMenuSelection",
    "BookingRule",
    "CalendarBlock",
    "AppSettings",
    "ReservationAccessToken",
]

from app.models.layout import VenueLayoutTemplate, LayoutAsset, ReservationLayout
