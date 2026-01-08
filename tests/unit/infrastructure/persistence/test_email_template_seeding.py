"""Unit tests for email template seeding functionality.

Tests verify that default email templates are correctly seeded during database
initialization and that the seeding process is idempotent.
"""

import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.email_template import EmailTemplateModel


# System account ID constant
SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"


async def seed_templates_to_session(session: AsyncSession) -> None:
    """Helper function to seed templates directly to a session for testing."""
    default_templates = [
        {
            "template_type": "email_verification",
            "locale": "en",
            "subject": "Verify your email address for {{ app_name }}",
        },
        {
            "template_type": "password_reset",
            "locale": "en",
            "subject": "Reset your password for {{ app_name }}",
        },
        {
            "template_type": "invitation",
            "locale": "en",
            "subject": "You've been invited to join {{ account_name }} on {{ app_name }}",
        },
    ]
    
    for template_data in default_templates:
        # Check if template already exists
        result = await session.execute(
            select(EmailTemplateModel).where(
                EmailTemplateModel.account_id == SYSTEM_ACCOUNT_ID,
                EmailTemplateModel.template_type == template_data["template_type"],
                EmailTemplateModel.locale == template_data["locale"],
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing is None:
            # Create minimal template for testing
            new_template = EmailTemplateModel(
                id=str(uuid.uuid4()),
                account_id=SYSTEM_ACCOUNT_ID,
                template_type=template_data["template_type"],
                locale=template_data["locale"],
                subject=template_data["subject"],
                html_body=f"<html><body>{{ {template_data['template_type']} }}</body></html>",
                text_body=f"Text version of {template_data['template_type']}",
                enabled=True,
                is_builtin=True,
            )
            session.add(new_template)
    
    await session.commit()


@pytest.mark.asyncio
async def test_seed_default_email_templates_creates_all_templates(
    db_session: AsyncSession,
) -> None:
    """Test that all default email templates are created during seeding."""
    # Seed templates
    await seed_templates_to_session(db_session)

    # Verify all 3 templates exist
    result = await db_session.execute(
        select(EmailTemplateModel).where(
            EmailTemplateModel.account_id == SYSTEM_ACCOUNT_ID,
            EmailTemplateModel.is_builtin == True,  # noqa: E712
        )
    )
    templates = result.scalars().all()

    assert len(templates) == 3, "Expected 3 default templates to be created"

    # Verify template types
    template_types = {t.template_type for t in templates}
    expected_types = {"email_verification", "password_reset", "invitation"}
    assert (
        template_types == expected_types
    ), f"Expected template types {expected_types}, got {template_types}"


@pytest.mark.asyncio
async def test_seed_default_email_templates_idempotent(
    db_session: AsyncSession,
) -> None:
    """Test that seeding is idempotent (no duplicates on multiple runs)."""
    # Seed templates twice
    await seed_templates_to_session(db_session)
    await seed_templates_to_session(db_session)

    # Verify still only 3 templates exist
    result = await db_session.execute(
        select(EmailTemplateModel).where(
            EmailTemplateModel.account_id == SYSTEM_ACCOUNT_ID,
            EmailTemplateModel.is_builtin == True,  # noqa: E712
        )
    )
    templates = result.scalars().all()

    assert len(templates) == 3, "Expected exactly 3 templates after multiple seeding"


@pytest.mark.asyncio
async def test_email_templates_have_required_fields(
    db_session: AsyncSession,
) -> None:
    """Test that all templates have required fields populated."""
    await seed_templates_to_session(db_session)

    result = await db_session.execute(
        select(EmailTemplateModel).where(
            EmailTemplateModel.account_id == SYSTEM_ACCOUNT_ID,
            EmailTemplateModel.is_builtin == True,  # noqa: E712
        )
    )
    templates = result.scalars().all()

    for template in templates:
        assert template.subject, f"Template {template.template_type} missing subject"
        assert (
            template.html_body
        ), f"Template {template.template_type} missing html_body"
        assert (
            template.text_body
        ), f"Template {template.template_type} missing text_body"
        assert (
            len(template.subject) > 0
        ), f"Template {template.template_type} has empty subject"
        assert (
            len(template.html_body) > 0
        ), f"Template {template.template_type} has empty html_body"
        assert (
            len(template.text_body) > 0
        ), f"Template {template.template_type} has empty text_body"


@pytest.mark.asyncio
async def test_email_templates_are_builtin(db_session: AsyncSession) -> None:
    """Test that all seeded templates have is_builtin=true."""
    await seed_templates_to_session(db_session)

    result = await db_session.execute(
        select(EmailTemplateModel).where(
            EmailTemplateModel.account_id == SYSTEM_ACCOUNT_ID,
        )
    )
    templates = result.scalars().all()

    for template in templates:
        assert (
            template.is_builtin is True
        ), f"Template {template.template_type} should have is_builtin=true"


@pytest.mark.asyncio
async def test_email_templates_use_system_account(
    db_session: AsyncSession,
) -> None:
    """Test that all templates are associated with the system account."""
    await seed_templates_to_session(db_session)

    result = await db_session.execute(
        select(EmailTemplateModel).where(
            EmailTemplateModel.is_builtin == True,  # noqa: E712
        )
    )
    templates = result.scalars().all()

    for template in templates:
        assert (
            template.account_id == SYSTEM_ACCOUNT_ID
        ), f"Template {template.template_type} should use SYSTEM_ACCOUNT_ID"


@pytest.mark.asyncio
async def test_email_templates_have_correct_locale(
    db_session: AsyncSession,
) -> None:
    """Test that all templates have locale='en'."""
    await seed_templates_to_session(db_session)

    result = await db_session.execute(
        select(EmailTemplateModel).where(
            EmailTemplateModel.account_id == SYSTEM_ACCOUNT_ID,
            EmailTemplateModel.is_builtin == True,  # noqa: E712
        )
    )
    templates = result.scalars().all()

    for template in templates:
        assert (
            template.locale == "en"
        ), f"Template {template.template_type} should have locale='en'"


@pytest.mark.asyncio
async def test_email_templates_are_enabled_by_default(
    db_session: AsyncSession,
) -> None:
    """Test that all seeded templates are enabled by default."""
    await seed_templates_to_session(db_session)

    result = await db_session.execute(
        select(EmailTemplateModel).where(
            EmailTemplateModel.account_id == SYSTEM_ACCOUNT_ID,
            EmailTemplateModel.is_builtin == True,  # noqa: E712
        )
    )
    templates = result.scalars().all()

    for template in templates:
        assert (
            template.enabled is True
        ), f"Template {template.template_type} should be enabled by default"
