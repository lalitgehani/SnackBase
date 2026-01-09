"""Unit tests for the AWS SES email provider."""

import unittest.mock as mock

import pytest
from botocore.exceptions import ClientError

from snackbase.infrastructure.services.email.aws_ses_provider import (
    AWSESProvider,
    AWSESSettings,
)


@pytest.fixture
def aws_ses_settings() -> AWSESSettings:
    """Fixture for AWS SES settings."""
    return AWSESSettings(
        region="us-east-1",
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        from_email="noreply@example.com",
        from_name="SnackBase Test",
    )


@pytest.fixture
def aws_ses_provider(aws_ses_settings: AWSESSettings) -> AWSESProvider:
    """Fixture for AWS SES provider."""
    return AWSESProvider(aws_ses_settings)


@pytest.mark.asyncio
async def test_aws_ses_send_email_success(aws_ses_provider: AWSESProvider) -> None:
    """Test successful email sending via AWS SES."""
    with mock.patch("boto3.client") as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        mock_ses.send_email.return_value = {"MessageId": "test-message-id-123"}

        success = await aws_ses_provider.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            html_body="<p>HTML Body</p>",
            text_body="Text Body",
            from_email="sender@example.com",
            from_name="Sender Name",
        )

        assert success is True
        mock_boto_client.assert_called_once_with(
            "ses",
            region_name="us-east-1",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        mock_ses.send_email.assert_called_once()

        # Verify call arguments
        call_args = mock_ses.send_email.call_args[1]
        assert "Sender Name <sender@example.com>" in call_args["Source"]
        assert call_args["Destination"]["ToAddresses"] == ["recipient@example.com"]
        assert call_args["Message"]["Subject"]["Data"] == "Test Subject"
        assert call_args["Message"]["Body"]["Html"]["Data"] == "<p>HTML Body</p>"
        assert call_args["Message"]["Body"]["Text"]["Data"] == "Text Body"


@pytest.mark.asyncio
async def test_aws_ses_send_email_with_reply_to(
    aws_ses_provider: AWSESProvider,
) -> None:
    """Test email sending with reply-to address."""
    with mock.patch("boto3.client") as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        mock_ses.send_email.return_value = {"MessageId": "test-message-id-123"}

        success = await aws_ses_provider.send_email(
            to="recipient@example.com",
            subject="Test Subject",
            html_body="<p>HTML Body</p>",
            text_body="Text Body",
            from_email="sender@example.com",
            from_name="Sender Name",
            reply_to="reply@example.com",
        )

        assert success is True
        call_args = mock_ses.send_email.call_args[1]
        assert call_args["ReplyToAddresses"] == ["reply@example.com"]


@pytest.mark.asyncio
async def test_aws_ses_send_email_message_rejected(
    aws_ses_provider: AWSESProvider,
) -> None:
    """Test handling of MessageRejected error."""
    with mock.patch("boto3.client") as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses

        error_response = {
            "Error": {
                "Code": "MessageRejected",
                "Message": "Email address is not verified.",
            }
        }
        mock_ses.send_email.side_effect = ClientError(error_response, "SendEmail")

        with pytest.raises(ClientError):
            await aws_ses_provider.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                html_body="<p>HTML Body</p>",
                text_body="Text Body",
                from_email="sender@example.com",
                from_name="Sender Name",
            )


@pytest.mark.asyncio
async def test_aws_ses_send_email_account_paused(
    aws_ses_provider: AWSESProvider,
) -> None:
    """Test handling of AccountSendingPausedException error."""
    with mock.patch("boto3.client") as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses

        error_response = {
            "Error": {
                "Code": "AccountSendingPausedException",
                "Message": "Account sending is paused.",
            }
        }
        mock_ses.send_email.side_effect = ClientError(error_response, "SendEmail")

        with pytest.raises(ClientError):
            await aws_ses_provider.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                html_body="<p>HTML Body</p>",
                text_body="Text Body",
                from_email="sender@example.com",
                from_name="Sender Name",
            )


@pytest.mark.asyncio
async def test_aws_ses_test_connection_success(
    aws_ses_provider: AWSESProvider,
) -> None:
    """Test successful connection test."""
    with mock.patch("boto3.client") as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        mock_ses.get_send_quota.return_value = {
            "Max24HourSend": 200.0,
            "SentLast24Hours": 50.0,
            "MaxSendRate": 1.0,
        }

        success, message = await aws_ses_provider.test_connection()

        assert success is True
        assert message is not None
        assert "50/200" in message
        assert "1" in message  # max send rate
        mock_ses.get_send_quota.assert_called_once()


@pytest.mark.asyncio
async def test_aws_ses_test_connection_invalid_credentials(
    aws_ses_provider: AWSESProvider,
) -> None:
    """Test connection test with invalid credentials."""
    with mock.patch("boto3.client") as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses

        error_response = {
            "Error": {
                "Code": "InvalidClientTokenId",
                "Message": "The security token included in the request is invalid.",
            }
        }
        mock_ses.get_send_quota.side_effect = ClientError(
            error_response, "GetSendQuota"
        )

        success, message = await aws_ses_provider.test_connection()

        assert success is False
        assert message is not None
        assert "InvalidClientTokenId" in message
        assert "security token" in message


@pytest.mark.asyncio
async def test_aws_ses_test_connection_sandbox_mode(
    aws_ses_provider: AWSESProvider,
) -> None:
    """Test connection test in sandbox mode (still returns quota)."""
    with mock.patch("boto3.client") as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        # In sandbox mode, quota is typically 200 emails per 24 hours
        mock_ses.get_send_quota.return_value = {
            "Max24HourSend": 200.0,
            "SentLast24Hours": 0.0,
            "MaxSendRate": 1.0,
        }

        success, message = await aws_ses_provider.test_connection()

        assert success is True
        assert message is not None
        # Sandbox mode typically has 200 email limit
        assert "200" in message
