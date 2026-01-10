"""Invitation API routes.

Provides endpoints for creating, accepting, listing, and cancelling user invitations.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.core.logging import get_logger
from snackbase.domain.services import default_password_validator
from snackbase.infrastructure.api.dependencies import (
    AuthenticatedUser,
    get_db_session,
    get_email_service,
    SYSTEM_ACCOUNT_ID,
)
from snackbase.infrastructure.api.schemas import (
    AccountResponse,
    AuthResponse,
    InvitationAcceptRequest,
    InvitationCreateRequest,
    InvitationListResponse,
    InvitationResponse,
    InvitationStatus,
    UserResponse,
)
from snackbase.infrastructure.auth import hash_password, jwt_service
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.persistence.models import (
    AccountModel,
    InvitationModel,
    RefreshTokenModel,
    UserModel,
)
from snackbase.infrastructure.persistence.repositories import (
    AccountRepository,
    InvitationRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from snackbase.infrastructure.services.email_service import EmailService
from snackbase.infrastructure.services.token_service import token_service

logger = get_logger(__name__)

router = APIRouter()


def get_invitation_status(invitation: InvitationModel) -> InvitationStatus:
    """Determine the status of an invitation.

    Args:
        invitation: Invitation model.

    Returns:
        InvitationStatus enum value.
    """
    if invitation.accepted_at is not None:
        return InvitationStatus.ACCEPTED
    # Convert expires_at to timezone-aware if it's naive
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        return InvitationStatus.EXPIRED
    else:
        return InvitationStatus.PENDING


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=InvitationResponse,
    responses={
        400: {"description": "Validation error or user already in account"},
        409: {"description": "Pending invitation already exists"},
    },
)
async def create_invitation(
    request: InvitationCreateRequest,
    current_user: AuthenticatedUser,
    email_service: EmailService = Depends(get_email_service),
    session: AsyncSession = Depends(get_db_session),
) -> InvitationResponse | JSONResponse:
    """Create a new invitation.

    Creates an invitation for a user to join the current user's account.
    Sends an invitation email with a secure token.

    Flow:
    1. Validate email format (handled by Pydantic)
    2. Check if user already exists in account
    3. Check if pending invitation exists
    4. Generate secure token
    5. Create invitation record
    6. Send invitation email
    7. Return invitation details (excluding token)
    """
    # Initialize repositories
    user_repo = UserRepository(session)
    invitation_repo = InvitationRepository(session)
    account_repo = AccountRepository(session)

    # Determine target account ID
    target_account_id = current_user.account_id
    
    if request.account_id:
        # Only superadmins can invite users to other accounts
        if current_user.account_id == SYSTEM_ACCOUNT_ID:
            target_account_id = request.account_id
        else:
             logger.warning(
                "Unauthorized attempt to set account_id in invitation",
                user_id=current_user.user_id,
                requested_account_id=request.account_id
            )
             return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Forbidden",
                    "message": "Only superadmins can invite users to other accounts",
                },
            )

    # 2. Check if user already exists in account
    if await user_repo.email_exists_in_account(request.email, target_account_id):
        logger.info(
            "Invitation creation failed: user already in account",
            email=request.email,
            account_id=target_account_id,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation error",
                "message": "User with this email already exists in this account",
            },
        )

    # 3. Check if pending invitation exists
    if await invitation_repo.check_pending_invitation_exists(
        request.email, target_account_id
    ):
        logger.info(
            "Invitation creation failed: pending invitation exists",
            email=request.email,
            account_id=target_account_id,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "Conflict",
                "message": "A pending invitation already exists for this email",
            },
        )

    # 4. Generate secure token
    invitation_token = token_service.generate_token(32)  # 64 hex characters

    # 5. Create invitation record
    settings = get_settings()
    invitation_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)

    invitation = InvitationModel(
        id=invitation_id,
        account_id=target_account_id,
        email=request.email,
        token=invitation_token,
        invited_by=current_user.user_id,
        expires_at=expires_at,
    )

    await invitation_repo.create_invitation(invitation)
    await session.commit()
    await session.refresh(invitation)

    logger.info(
        "Invitation created successfully",
        invitation_id=invitation_id,
        email=request.email,
        account_id=target_account_id,
        invited_by=current_user.user_id,
    )

    # 6. Send invitation email
    account = await account_repo.get_by_id(current_user.account_id)
    account_name = account.name if account else current_user.account_id

    # Get inviter's user record to get their email/name
    inviter = await user_repo.get_by_id(current_user.user_id)
    inviter_name = inviter.email if inviter else current_user.email

    try:
        # TODO: Get app_url from settings service when available
        # For now, construct from request or use default
        app_url = "http://localhost:8000"  
        invitation_url = f"{app_url}/accept-invitation?token={invitation_token}"
        
        email_sent = await email_service.send_template_email(
            session=session,
            to=request.email,
            template_type="invitation",
            variables={
                "invitation_url": invitation_url,
                "token": invitation_token,
                "email": request.email,
                "account_name": account_name,
                "invited_by": inviter_name,
                "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            },
            account_id=current_user.account_id,
        )
        
        if email_sent:
            invitation.email_sent = True
            invitation.email_sent_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(invitation)
            
    except Exception as e:
        logger.error(
            "Failed to send invitation email",
            error=str(e),
            email=request.email,
            invitation_id=invitation_id
        )
        # Continue execution - invitation is created even if email fails
        # The UI can show email_sent=False status

    # 7. Return invitation details (including token)
    return InvitationResponse(
        id=invitation.id,
        account_id=invitation.account_id,
        account_code=account.account_code if account else "UNKNOWN",
        email=invitation.email,
        invited_by=invitation.invited_by,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        created_at=invitation.created_at,
        email_sent=invitation.email_sent,
        email_sent_at=invitation.email_sent_at,
        status=get_invitation_status(invitation),
        token=invitation.token,
    )

@router.post(
    "/{invitation_id}/resend",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Invitation not found"},
        400: {"description": "Cannot resend accepted or expired invitation"},
    },
)
async def resend_invitation(
    invitation_id: str,
    current_user: AuthenticatedUser,
    email_service: EmailService = Depends(get_email_service),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """Resend an invitation email.
    
    Resends the invitation email for a pending invitation.
    """
    invitation_repo = InvitationRepository(session)
    account_repo = AccountRepository(session)
    user_repo = UserRepository(session)
    
    # 1. Get invitation
    invitation = await invitation_repo.get_by_id(invitation_id)
    if invitation is None or invitation.account_id != current_user.account_id:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Not found", "message": "Invitation not found"},
        )
        
    # 2. Check status
    invitation_status = get_invitation_status(invitation)
    if invitation_status != InvitationStatus.PENDING:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation error", 
                "message": f"Cannot resend invitation with status: {invitation_status}"
            },
        )
        
    # 3. Send email
    account = await account_repo.get_by_id(current_user.account_id)
    account_name = account.name if account else current_user.account_id
    
    inviter = await user_repo.get_by_id(invitation.invited_by)
    inviter_name = inviter.email if inviter else "Team Member"
    
    try:
        app_url = "http://localhost:8000"  # TODO: Config
        invitation_url = f"{app_url}/accept-invitation?token={invitation.token}"
        
        # Ensure expires_at is timezone-aware for strftime
        expires_at = invitation.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        email_sent = await email_service.send_template_email(
            session=session,
            to=invitation.email,
            template_type="invitation",
            variables={
                "invitation_url": invitation_url,
                "token": invitation.token,
                "email": invitation.email,
                "account_name": account_name,
                "invited_by": inviter_name,
                "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            },
            account_id=current_user.account_id,
        )
        
        if email_sent:
            invitation.email_sent = True
            invitation.email_sent_at = datetime.now(timezone.utc)
            await session.commit()
            
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Invitation email resent successfully"},
        )
        
    except Exception as e:
        logger.error(
            "Failed to resend invitation email",
            error=str(e),
            invitation_id=invitation_id
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal error", "message": "Failed to send email"},
        )



@router.post(
    "/{token}/accept",
    status_code=status.HTTP_200_OK,
    response_model=AuthResponse,
    responses={
        400: {"description": "Validation error"},
        404: {"description": "Invalid, expired, or already accepted token"},
    },
)
async def accept_invitation(
    token: str,
    request: InvitationAcceptRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse | JSONResponse:
    """Accept an invitation and create a user account.

    Validates the invitation token, creates a user account with the provided
    password, and returns authentication tokens.

    Flow:
    1. Validate token exists
    2. Validate token not expired
    3. Validate token not already accepted
    4. Validate password strength
    5. Create user account
    6. Mark invitation as accepted
    7. Generate JWT tokens
    8. Return auth response
    """
    # Initialize repositories
    invitation_repo = InvitationRepository(session)
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)
    account_repo = AccountRepository(session)

    # 1. Validate token exists
    invitation = await invitation_repo.get_by_token(token)
    if invitation is None:
        logger.info("Invitation acceptance failed: token not found", token=token[:8])
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": "Invalid invitation token",
            },
        )

    # 2. Validate token not expired
    # Convert expires_at to timezone-aware if it's naive
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        logger.info(
            "Invitation acceptance failed: token expired",
            invitation_id=invitation.id,
            expired_at=invitation.expires_at.isoformat(),
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": "Invitation has expired",
            },
        )

    # 3. Validate token not already accepted
    if invitation.accepted_at is not None:
        logger.info(
            "Invitation acceptance failed: already accepted",
            invitation_id=invitation.id,
            accepted_at=invitation.accepted_at.isoformat(),
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": "Invitation has already been accepted",
            },
        )

    # 4. Validate password strength
    password_errors = default_password_validator.validate(request.password)
    if password_errors:
        logger.info(
            "Invitation acceptance failed: password validation",
            invitation_id=invitation.id,
            error_count=len(password_errors),
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation error",
                "details": [
                    {"field": e.field, "message": e.message, "code": e.code}
                    for e in password_errors
                ],
            },
        )

    # 5. Create user account
    # Get default role (user) or use role from invitation if specified
    # For now, we'll use the default "user" role
    user_role = await role_repo.get_by_name("user")
    if user_role is None:
        logger.error("User role not found in database")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal error", "message": "Role configuration error"},
        )

    password_hash = hash_password(request.password)

    user = UserModel(
        id=str(uuid.uuid4()),
        account_id=invitation.account_id,
        email=invitation.email,
        password_hash=password_hash,
        role_id=user_role.id,
        is_active=True,
    )
    await user_repo.create(user)

    # 6. Mark invitation as accepted
    await invitation_repo.mark_as_accepted(invitation.id)

    # Commit the transaction
    await session.commit()

    # Refresh to get updated timestamps
    await session.refresh(user)
    await session.refresh(invitation)

    logger.info(
        "Invitation accepted successfully",
        invitation_id=invitation.id,
        user_id=user.id,
        email=user.email,
        account_id=invitation.account_id,
    )

    # 7. Generate JWT tokens
    access_token = jwt_service.create_access_token(
        user_id=user.id,
        account_id=invitation.account_id,
        email=user.email,
        role=user_role.name,
    )
    refresh_token, token_id = jwt_service.create_refresh_token(
        user_id=user.id,
        account_id=invitation.account_id,
    )
    expires_in = jwt_service.get_expires_in()

    # Store refresh token in database for revocation tracking
    settings = get_settings()
    refresh_token_repo = RefreshTokenRepository(session)
    refresh_token_model = RefreshTokenModel(
        id=token_id,
        token_hash=refresh_token_repo.hash_token(refresh_token),
        user_id=user.id,
        account_id=invitation.account_id,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
    )
    await refresh_token_repo.create(refresh_token_model)
    await session.commit()

    # Get account details
    account = await account_repo.get_by_id(invitation.account_id)

    # 8. Return auth response
    return AuthResponse(
        token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        account=AccountResponse(
            id=account.id,
            slug=account.slug,
            name=account.name,
            created_at=account.created_at,
        ),
        user=UserResponse(
            id=user.id,
            email=user.email,
            role=user_role.name,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=InvitationListResponse,
)
async def list_invitations(
    current_user: AuthenticatedUser,
    status_filter: InvitationStatus | None = None,
    account_id: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> InvitationListResponse:
    """List invitations.

    For superadmins: lists all invitations or filters by account_id.
    For regular users: lists invitations for their own account only.

    Args:
        current_user: Authenticated user context.
        status_filter: Optional status filter (pending, accepted, expired).
        account_id: Optional account ID filter (superadmin only).
        session: Database session.

    Returns:
        List of invitations.
    """
    invitation_repo = InvitationRepository(session)
    
    # Determine target account ID
    target_account_id = current_user.account_id
    
    # Check if superadmin
    if current_user.account_id == SYSTEM_ACCOUNT_ID:
        # Superadmin can filter by account_id or list all (None)
        target_account_id = account_id
    elif account_id and account_id != current_user.account_id:
        # Regular user tried to filter by another account -> Forbidden or ignore?
        # Let's ignore it and force their own account to avoid leaking existence
        target_account_id = current_user.account_id

    # Get invitations (using new list_invitations method that supports None for account_id)
    invitations = await invitation_repo.list_invitations(
        account_id=target_account_id,
        status=status_filter.value if status_filter else None,
    )

    logger.info(
        "Listed invitations",
        account_id=current_user.account_id,
        target_account_id=target_account_id,
        count=len(invitations),
        status_filter=status_filter.value if status_filter else "all",
    )

    # Convert to response models
    invitation_responses = []
    for inv in invitations:
        # Use account code from joined relationship if available
        # Need to handle case where relationship might not be loaded if repository didn't join it
        # But we updated repository to join it.
        account_code = "UNKNOWN"
        if hasattr(inv, "account") and inv.account:
            account_code = inv.account.account_code
            
        invitation_responses.append(
            InvitationResponse(
                id=inv.id,
                account_id=inv.account_id,
                account_code=account_code,
                email=inv.email,
                invited_by=inv.invited_by,
                expires_at=inv.expires_at,
                accepted_at=inv.accepted_at,
                created_at=inv.created_at,
                email_sent=inv.email_sent,
                email_sent_at=inv.email_sent_at,
                status=get_invitation_status(inv),
                token=inv.token,
            )
        )

    return InvitationListResponse(
        invitations=invitation_responses,
        total=len(invitation_responses),
    )


@router.delete(
    "/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Invitation not found"},
    },
)
async def cancel_invitation(
    invitation_id: str,
    current_user: AuthenticatedUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Cancel an invitation.

    Deletes an invitation from the database. Only invitations belonging to
    the current user's account can be cancelled.

    Args:
        invitation_id: ID of the invitation to cancel.
        current_user: Authenticated user context.
        session: Database session.

    Raises:
        HTTPException: 404 if invitation not found or doesn't belong to account.
    """
    invitation_repo = InvitationRepository(session)

    # Get invitation to verify it belongs to the user's account
    invitation = await invitation_repo.get_by_id(invitation_id)

    if invitation is None or invitation.account_id != current_user.account_id:
        logger.info(
            "Invitation cancellation failed: not found or wrong account",
            invitation_id=invitation_id,
            account_id=current_user.account_id,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Not found",
                "message": "Invitation not found",
            },
        )

    # Delete the invitation
    await invitation_repo.cancel_invitation(invitation_id)
    await session.commit()

    logger.info(
        "Invitation cancelled successfully",
        invitation_id=invitation_id,
        account_id=current_user.account_id,
    )
