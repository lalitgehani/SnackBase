"""Persistence repositories for database operations."""

from snackbase.infrastructure.persistence.repositories.account_repository import (
    AccountRepository,
)
from snackbase.infrastructure.persistence.repositories.collection_repository import (
    CollectionRepository,
)
from snackbase.infrastructure.persistence.repositories.configuration_repository import (
    ConfigurationRepository,
)
from snackbase.infrastructure.persistence.repositories.email_log_repository import (
    EmailLogRepository,
)
from snackbase.infrastructure.persistence.repositories.email_template_repository import (
    EmailTemplateRepository,
)
from snackbase.infrastructure.persistence.repositories.email_verification_repository import (
    EmailVerificationRepository,
)
from snackbase.infrastructure.persistence.repositories.invitation_repository import (
    InvitationRepository,
)
from snackbase.infrastructure.persistence.repositories.permission_repository import (
    PermissionRepository,
)
from snackbase.infrastructure.persistence.repositories.record_repository import (
    RecordRepository,
)
from snackbase.infrastructure.persistence.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from snackbase.infrastructure.persistence.repositories.role_repository import (
    RoleRepository,
)
from snackbase.infrastructure.persistence.repositories.user_repository import (
    UserRepository,
)
from snackbase.infrastructure.persistence.repositories.audit_log_repository import (
    AuditLogRepository,
)
from snackbase.infrastructure.persistence.repositories.group_repository import (
    GroupRepository,
)
from snackbase.infrastructure.persistence.repositories.macro_repository import (
    MacroRepository,
)
from snackbase.infrastructure.persistence.repositories.oauth_state_repository import (
    OAuthStateRepository,
)

__all__ = [
    "AccountRepository",
    "AuditLogRepository",
    "CollectionRepository",
    "ConfigurationRepository",
    "EmailVerificationRepository",
    "GroupRepository",
    "InvitationRepository",
    "MacroRepository",
    "OAuthStateRepository",
    "PermissionRepository",
    "RecordRepository",
    "RefreshTokenRepository",
    "RoleRepository",
    "UserRepository",
]
