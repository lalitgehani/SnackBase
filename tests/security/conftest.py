import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator, Dict, Any, Optional

from tests.security.reporter.html_reporter import HTMLReporter


class AttackClient:
    """A wrapper around AsyncClient that logs all requests to the HTMLReporter."""

    def __init__(self, client: AsyncClient, reporter: HTMLReporter):
        self.client = client
        self.reporter = reporter

    async def _make_request(
        self,
        method: str,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        description: str = "",
        **kwargs
    ) -> Any:
        response = await self.client.request(method, url, json=json, **kwargs)

        status = "PASSED"
        # Try to parse response body
        try:
            response_body = response.json()
        except Exception:
            response_body = response.text

        self.reporter.log_request(
            description=description or f"{method} {url}",
            method=method,
            url=url,
            headers=dict(kwargs.get("headers", {})),
            body=json,
            response_status=response.status_code,
            response_body=response_body,
            status=status
        )
        return response

    async def get(self, url: str, description: str = "", **kwargs) -> Any:
        return await self._make_request("GET", url, description=description, **kwargs)

    async def post(self, url: str, json: Optional[Dict[str, Any]] = None, description: str = "", **kwargs) -> Any:
        return await self._make_request("POST", url, json=json, description=description, **kwargs)

    async def put(self, url: str, json: Optional[Dict[str, Any]] = None, description: str = "", **kwargs) -> Any:
        return await self._make_request("PUT", url, json=json, description=description, **kwargs)

    async def delete(self, url: str, description: str = "", **kwargs) -> Any:
        return await self._make_request("DELETE", url, description=description, **kwargs)

    async def patch(self, url: str, json: Optional[Dict[str, Any]] = None, description: str = "", **kwargs) -> Any:
        return await self._make_request("PATCH", url, json=json, description=description, **kwargs)


@pytest.fixture(scope="session")
def security_reporter():
    """Shared reporter for the entire security test session."""
    reporter = HTMLReporter(suite_name="Security Audit Suite")
    yield reporter
    # Generate the single consolidated report at the end of the session
    report_path = reporter.generate()
    print(f"\nConsolidated security report generated: {report_path}")


@pytest.fixture(autouse=True)
def setup_security_test_section(request, security_reporter):
    """Automatically starts a new section in the reporter for each test."""
    # Only for security tests
    if "security" in request.node.fspath.strpath:
        security_reporter.start_section(request.node.name)
    yield


@pytest.fixture
def html_reporter(security_reporter):
    """Provide the shared reporter instance to tests."""
    return security_reporter


@pytest_asyncio.fixture
async def attack_client(client: AsyncClient, html_reporter: HTMLReporter) -> AttackClient:
    """An HTTP client that logs all requests to the security reporter."""
    return AttackClient(client, html_reporter)
