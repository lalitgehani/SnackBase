import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

# Finding IDs from the VAPT of 2026-08-09, e.g. "C-01 fix pending".
_FINDING_RE = re.compile(r"\b([CHM]-\d{2})\b")

# Security-suite outcome vocabulary. This is deliberately not pytest's:
#   VULNERABLE — the test asserts secure behaviour and that behaviour does not
#                hold. Reported by pytest as an expected failure; for a security
#                audit it is a confirmed, unfixed finding and the headline
#                result of the whole run.
#   FIXED      — the asserted secure behaviour now holds, so the xfail marker is
#                stale and must be removed in the same change as the fix.
#   PASSED     — a boundary that holds.
STATUS_VULNERABLE = "VULNERABLE"
STATUS_FIXED = "FIXED"
STATUS_PASSED = "PASSED"
STATUS_FAILED = "FAILED"
STATUS_ERROR = "ERROR"
STATUS_SKIPPED = "SKIPPED"

# Statuses that must fail the build.
_BREAKING_STATUSES = {STATUS_FAILED, STATUS_ERROR, STATUS_FIXED}


class HTMLReporter:
    """Generates a consolidated HTML report for security tests."""

    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        self.start_time = datetime.now(UTC)
        self.sections: list[dict[str, Any]] = []
        self.overall_status = STATUS_PASSED

        # Setup paths
        self.base_dir = Path(__file__).parent.parent.parent.parent
        self.report_dir = self.base_dir / "tests" / "security-reports"
        self.template_dir = Path(__file__).parent / "templates"

        self.report_dir.mkdir(exist_ok=True)
        self.current_section: dict[str, Any] | None = None
        self._by_nodeid: dict[str, dict[str, Any]] = {}

    def start_section(self, test_name: str, nodeid: str | None = None) -> None:
        """Start a new test section in the report.

        The section opens with no status at all: it is filled in by
        ``record_outcome`` once pytest knows how the test actually ended.
        """
        self.current_section = {
            "test_name": test_name,
            "nodeid": nodeid,
            "requests": [],
            "vulnerabilities": [],
            "status": None,
            "detail": "",
            "finding": None,
            "duration_ms": 0,
        }
        self.sections.append(self.current_section)
        if nodeid:
            self._by_nodeid[nodeid] = self.current_section

    def record_outcome(
        self,
        nodeid: str,
        status: str,
        detail: str = "",
        duration: float = 0.0,
    ) -> None:
        """Record a test's real pytest outcome against its section."""
        section = self._by_nodeid.get(nodeid)
        if section is None:
            # No fixture ran (e.g. a collection-time error) — keep the evidence
            # rather than dropping the result on the floor.
            section = {
                "test_name": nodeid.rsplit("::", 1)[-1],
                "nodeid": nodeid,
                "requests": [],
                "vulnerabilities": [],
                "status": None,
                "detail": "",
                "finding": None,
                "duration_ms": 0,
            }
            self.sections.append(section)
            self._by_nodeid[nodeid] = section

        section["status"] = status
        section["detail"] = detail
        section["duration_ms"] = int(duration * 1000)

        match = _FINDING_RE.search(detail or "")
        section["finding"] = match.group(1) if match else None

        if status in _BREAKING_STATUSES:
            self.overall_status = STATUS_FAILED
        elif status == STATUS_VULNERABLE and self.overall_status == STATUS_PASSED:
            self.overall_status = STATUS_VULNERABLE

    def log_request(
        self,
        description: str,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: Any | None = None,
        response_status: int = 0,
        response_body: Any | None = None,
        status: str = "ALLOWED",
    ) -> None:
        """Log an HTTP request and its response to the current section."""
        if not self.current_section:
            self.start_section("Default Section")

        self.current_section["requests"].append({
            "description": description,
            "method": method,
            "url": url,
            "headers": headers,
            "body": body,
            "response_status": response_status,
            "response_body": response_body,
            "status": status,
        })

    def log_vulnerability(self, severity: str, description: str) -> None:
        """Log a detected vulnerability to the current section."""
        if not self.current_section:
            self.start_section("Default Section")

        self.current_section["vulnerabilities"].append({
            "severity": severity,
            "description": description,
        })

    def _findings_summary(self) -> list[dict[str, Any]]:
        """Group confirmed findings by their VAPT finding ID."""
        grouped: dict[str, list[str]] = {}
        for section in self.sections:
            if section["status"] != STATUS_VULNERABLE:
                continue
            key = section["finding"] or "untagged"
            grouped.setdefault(key, []).append(section["test_name"])

        return [
            {"finding": finding, "tests": sorted(tests), "count": len(tests)}
            for finding, tests in sorted(grouped.items())
        ]

    def generate(self) -> str:
        """Generate the consolidated HTML report."""
        duration = (datetime.now(UTC) - self.start_time).total_seconds() * 1000

        env = Environment(loader=FileSystemLoader(str(self.template_dir)))
        template = env.get_template("report_template.html")

        counts = Counter(section["status"] or STATUS_SKIPPED for section in self.sections)
        total_requests = sum(len(section["requests"]) for section in self.sections)

        html_content = template.render(
            suite_name=self.suite_name,
            timestamp=self.timestamp,
            overall_status=self.overall_status,
            total_tests=len(self.sections),
            total_requests=total_requests,
            passed_count=counts[STATUS_PASSED],
            vulnerable_count=counts[STATUS_VULNERABLE],
            fixed_count=counts[STATUS_FIXED],
            failed_count=counts[STATUS_FAILED] + counts[STATUS_ERROR],
            skipped_count=counts[STATUS_SKIPPED],
            findings=self._findings_summary(),
            duration_ms=int(duration),
            sections=self.sections,
        )

        filename = f"security_audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report_path = self.report_dir / filename

        with open(report_path, "w") as f:
            f.write(html_content)

        return str(report_path)
