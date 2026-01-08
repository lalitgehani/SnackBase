"""Unit tests for the SMTP email provider."""

import unittest.mock as mock
import pytest
from aiosmtplib import SMTP

from snackbase.infrastructure.services.email.smtp_provider import (
    SMTPProvider,
    SMTPSettings,
)


@pytest.fixture
def smtp_settings() -> SMTPSettings:
    """Fixture for SMTP settings."""
    return SMTPSettings(
        host="smtp.example.com",
        port=587,
        username="test_user",
        password="test_password",
        from_email="noreply@example.com",
        from_name="SnackBase Test",
    )


@pytest.fixture
def smtp_provider(smtp_settings: SMTPSettings) -> SMTPProvider:
    """Fixture for SMTP provider."""
    return SMTPProvider(smtp_settings)


@pytest.mark.asyncio
async def test_smtp_send_email_success(smtp_provider: SMTPProvider) -> None:
    """Test successful email sending."""
    with mock.patch("aiosmtplib.SMTP", autospec=True) as mock_smtp_class:
        mock_smtp = mock_smtp_class.return_value.__aenter__.return_value
        
        success = await smtp_provider.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            html_body="<p>HTML Body</p>",
            text_body="Text Body",
            from_email="sender@example.com",
            from_name="Sender Name",
        )
        
        assert success is True
        mock_smtp_class.assert_called_once_with(
            hostname="smtp.example.com",
            port=587,
            use_tls=False,
            timeout=10,
        )
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("test_user", "test_password")
        mock_smtp.send_message.assert_called_once()
        
        # Verify message contents
        sent_message = mock_smtp.send_message.call_args[0][0]
        assert sent_message["Subject"] == "Test Subject"
        assert sent_message["To"] == "recipient@example.com"
        assert "Sender Name <sender@example.com>" in sent_message["From"]


@pytest.mark.asyncio
async def test_smtp_send_email_ssl_success(smtp_settings: SMTPSettings) -> None:
    """Test successful email sending with SSL."""
    ssl_settings = smtp_settings.model_copy(update={"port": 465, "use_ssl": True, "use_tls": False})
    provider = SMTPProvider(ssl_settings)
    
    with mock.patch("aiosmtplib.SMTP", autospec=True) as mock_smtp_class:
        mock_smtp = mock_smtp_class.return_value.__aenter__.return_value
        
        success = await provider.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            html_body="<p>HTML Body</p>",
            text_body="Text Body",
            from_email="sender@example.com",
            from_name="Sender Name",
        )
        
        assert success is True
        mock_smtp_class.assert_called_once_with(
            hostname="smtp.example.com",
            port=465,
            use_tls=True, # aiosmtplib uses use_tls for SSL on connection
            timeout=10,
        )
        mock_smtp.starttls.assert_not_called()
        mock_smtp.login.assert_called_once()


@pytest.mark.asyncio
async def test_smtp_test_connection_success(smtp_provider: SMTPProvider) -> None:
    """Test successful connection test."""
    with mock.patch("aiosmtplib.SMTP", autospec=True) as mock_smtp_class:
        success, error = await smtp_provider.test_connection()
        
        assert success is True
        assert error is None
        
        mock_smtp = mock_smtp_class.return_value.__aenter__.return_value
        mock_smtp.login.assert_called_once()


@pytest.mark.asyncio
async def test_smtp_test_connection_failure(smtp_provider: SMTPProvider) -> None:
    """Test failed connection test."""
    with mock.patch("aiosmtplib.SMTP", autospec=True) as mock_smtp_class:
        mock_smtp = mock_smtp_class.return_value.__aenter__.return_value
        mock_smtp.login.side_effect = Exception("Authentication failed")
        
        success, error = await smtp_provider.test_connection()
        
        assert success is False
        assert "Authentication failed" in error
