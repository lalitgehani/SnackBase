"""Domain entities for SnackBase.

Entities are pure Python dataclasses that represent core business concepts.
They have no dependencies on infrastructure or external frameworks.
"""

from snackbase.domain.entities.account import Account
from snackbase.domain.entities.collection import Collection
from snackbase.domain.entities.group import Group
from snackbase.domain.entities.invitation import Invitation
from snackbase.domain.entities.role import Role
from snackbase.domain.entities.user import User

__all__ = [
    "Account",
    "Collection",
    "Group",
    "Invitation",
    "Role",
    "User",
]
