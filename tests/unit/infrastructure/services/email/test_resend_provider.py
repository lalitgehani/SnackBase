"""Unit tests for the Resend email provider."""

import unittest.mock as mock

import pytest
import resend

from snackbase.infrastructure.services.email.resend_provider import (
    ResendProvider,
    ResendSettings,
)


@pytest.fixture
def resend_settings() -> ResendSettings:
    """Fixture for Resend settings."""
    return ResendSettings(
        api_key="re_test_api_key_123456789",
        from_email="noreply@example.com",
        from_name="SnackBase Test",
    )


@pytest.fixture
def resend_provider(resend_settings: ResendSettings) -> ResendProvider:
    """Fixture for Resend provider."""
    return ResendProvider(resend_settings)


@pytest.mark.asyncio
async def test_resend_send_email_success(resend_provider: ResendProvider) -> None:
    """Test successful email sending via Resend."""
    with mock.patch("resend.Emails.send") as mock_send:
        mock_send.return_value = {"id": "test-email-id-123"}

        success = await resend_provider.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            html_body="<p>HTML Body</p>",
            text_body="Text Body",
            from_email="sender@example.com",
            from_name="Sender Name",
        )

        assert success is True
        mock_send.assert_called_once()

        # Verify call arguments
        call_args = mock_send.call_args[0][0]
        assert "Sender Name <sender@example.com>" in call_args["from"]
        assert call_args["to"] == ["recipient@example.com"]
        assert call_args["subject"] == "Test Subject"
        assert call_args["html"] == "<p>HTML Body</p>"
        assert call_args["text"] == "Text Body"


@pytest.mark.asyncio
async def test_resend_send_email_with_reply_to(
    resend_provider: ResendProvider,
) -> None:
    """Test email sending with reply-to address."""
    with mock.patch("resend.Emails.send") as mock_send:
        mock_send.return_value = {"id": "test-email-id-123"}

        success = await resend_provider.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            html_body="<p>HTML Body</p>",
            text_body="Text Body",
            from_email="sender@example.com",
            from_name="Sender Name",
            reply_to="reply@example.com",
        )

        assert success is True
        call_args = mock_send.call_args[0][0]
        assert call_args["reply_to"] == "reply@example.com"


@pytest.mark.asyncio
async def test_resend_send_email_invalid_api_key(
    resend_provider: ResendProvider,
) -> None:
    """Test handling of invalid API key error."""
    with mock.patch("resend.Emails.send") as mock_send:
        error = Exception("Invalid API key")
        mock_send.side_effect = error

        with pytest.raises(Exception):
            await resend_provider.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                html_body="<p>HTML Body</p>",
                text_body="Text Body",
                from_email="sender@example.com",
                from_name="Sender Name",
            )


@pytest.mark.asyncio
async def test_resend_send_email_rate_limit(
    resend_provider: ResendProvider,
) -> None:
    """Test handling of rate limit error."""
    with mock.patch("resend.Emails.send") as mock_send:
        error = Exception("Rate limit exceeded. Please try again later.")
        mock_send.side_effect = error

        with pytest.raises(Exception):
            await resend_provider.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                html_body="<p>HTML Body</p>",
                text_body="Text Body",
                from_email="sender@example.com",
                from_name="Sender Name",
            )


@pytest.mark.asyncio
async def test_resend_send_email_domain_not_verified(
    resend_provider: ResendProvider,
) -> None:
    """Test handling of domain not verified error."""
    with mock.patch("resend.Emails.send") as mock_send:
        error = Exception("Domain not verified. Please verify your domain in Resend.")
        mock_send.side_effect = error

        with pytest.raises(Exception):
            await resend_provider.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                html_body="<p>HTML Body</p>",
                text_body="Text Body",
                from_email="sender@example.com",
                from_name="Sender Name",
            )


@pytest.mark.asyncio
async def test_resend_test_connection_success(
    resend_provider: ResendProvider,
) -> None:
    """Test successful connection test."""
    with mock.patch("resend.Domains.list") as mock_list:
        mock_list.return_value = {
            "data": [
                {"id": "domain-1", "name": "example.com"},
                {"id": "domain-2", "name": "test.com"},
            ]
        }

        success, message = await resend_provider.test_connection()

        assert success is True
        assert message is not None
        assert "successful" in message.lower()
        assert "valid" in message.lower()
        mock_list.assert_called_once()


@pytest.mark.asyncio
async def test_resend_test_connection_invalid_api_key(
    resend_provider: ResendProvider,
) -> None:
    """Test connection test with invalid API key."""
    with mock.patch("resend.Domains.list") as mock_list:
        error = Exception("Invalid API key")
        mock_list.side_effect = error

        success, message = await resend_provider.test_connection()

        assert success is False
        assert message is not None
        assert "Invalid API key" in message


@pytest.mark.asyncio
async def test_resend_test_connection_unauthorized(
    resend_provider: ResendProvider,
) -> None:
    """Test connection test with unauthorized error."""
    with mock.patch("resend.Domains.list") as mock_list:
        error = Exception("Unauthorized")
        mock_list.side_effect = error

        success, message = await resend_provider.test_connection()

        assert success is False
        assert message is not None
        assert "Invalid API key" in message


@pytest.mark.asyncio
async def test_resend_test_connection_rate_limit(
    resend_provider: ResendProvider,
) -> None:
    """Test connection test with rate limit error."""
    with mock.patch("resend.Domains.list") as mock_list:
        error = Exception("Rate limit exceeded")
        mock_list.side_effect = error

        success, message = await resend_provider.test_connection()

        assert success is False
        assert message is not None
        assert "Rate limit" in message
