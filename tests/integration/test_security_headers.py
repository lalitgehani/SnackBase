"""Integration tests for security headers middleware.

These tests verify that security headers are properly set on all HTTP responses
and that the headers vary correctly between development and production environments.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_security_headers_in_development(client: AsyncClient):
    """Verify security headers are set in development (no HSTS)."""
    response = await client.get("/health")
    
    assert response.status_code == 200
    
    # Basic security headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    
    # CSP and Permissions Policy
    assert "Content-Security-Policy" in response.headers
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    
    assert "Permissions-Policy" in response.headers
    permissions = response.headers["Permissions-Policy"]
    assert "geolocation=()" in permissions
    
    # Referrer Policy
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    
    # HSTS should NOT be present in development
    assert "Strict-Transport-Security" not in response.headers


@pytest.mark.asyncio
async def test_security_headers_on_api_endpoints(client: AsyncClient):
    """Verify security headers are set on API endpoints."""
    response = await client.get("/api/v1")
    
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "Content-Security-Policy" in response.headers
    assert "Permissions-Policy" in response.headers
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_security_headers_on_404(client: AsyncClient):
    """Verify security headers are set even on 404 responses."""
    response = await client.get("/nonexistent-endpoint")
    
    assert response.status_code == 404
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers


@pytest.mark.asyncio
async def test_csp_header_format(client: AsyncClient):
    """Verify CSP header is properly formatted."""
    response = await client.get("/health")
    
    csp = response.headers["Content-Security-Policy"]
    
    # Verify key CSP directives
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self' 'unsafe-inline'" in csp  # Allow inline styles for React
    assert "img-src 'self' data:" in csp  # Allow data URIs for images
    assert "font-src 'self'" in csp
    assert "connect-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp  # Prevent iframe embedding


@pytest.mark.asyncio
async def test_permissions_policy_format(client: AsyncClient):
    """Verify Permissions-Policy header is properly formatted."""
    response = await client.get("/health")
    
    permissions = response.headers["Permissions-Policy"]
    
    # Verify key permissions are restricted
    assert "geolocation=()" in permissions
    assert "microphone=()" in permissions
    assert "camera=()" in permissions
    assert "payment=()" in permissions
