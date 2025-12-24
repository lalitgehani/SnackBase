"""SQLAlchemy models for SnackBase core system tables.

All models inherit from the Base class defined in database.py and are
automatically created on application startup in development mode.
"""

from snackbase.infrastructure.persistence.models.account import AccountModel
from snackbase.infrastructure.persistence.models.collection import CollectionModel
from snackbase.infrastructure.persistence.models.group import GroupModel
from snackbase.infrastructure.persistence.models.invitation import InvitationModel
from snackbase.infrastructure.persistence.models.permission import PermissionModel
from snackbase.infrastructure.persistence.models.refresh_token import RefreshTokenModel
from snackbase.infrastructure.persistence.models.role import RoleModel
from snackbase.infrastructure.persistence.models.user import UserModel
from snackbase.infrastructure.persistence.models.users_groups import UsersGroupsModel

__all__ = [
    "AccountModel",
    "CollectionModel",
    "GroupModel",
    "InvitationModel",
    "PermissionModel",
    "RefreshTokenModel",
    "RoleModel",
    "UserModel",
    "UsersGroupsModel",
]

