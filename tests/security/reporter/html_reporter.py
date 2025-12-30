import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader


class HTMLReporter:
    """Generates a consolidated HTML report for security tests."""

    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        self.start_time = datetime.now(timezone.utc)
        self.sections: List[Dict[str, Any]] = []
        self.overall_status = "PASSED"
        
        # Setup paths
        self.base_dir = Path(__file__).parent.parent.parent.parent
        self.report_dir = self.base_dir / "tests" / "security-reports"
        self.template_dir = Path(__file__).parent / "templates"
        
        self.report_dir.mkdir(exist_ok=True)
        self.current_section: Optional[Dict[str, Any]] = None

    def start_section(self, test_name: str):
        """Start a new test section in the report."""
        self.current_section = {
            "test_name": test_name,
            "requests": [],
            "vulnerabilities": [],
            "status": "PASSED"
        }
        self.sections.append(self.current_section)

    def log_request(
        self,
        description: str,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        response_status: int = 0,
        response_body: Optional[Any] = None,
        status: str = "PASSED",
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
        if status == "FAILED":
            self.current_section["status"] = "FAILED"
            self.overall_status = "FAILED"

    def log_vulnerability(self, severity: str, description: str) -> None:
        """Log a detected vulnerability to the current section."""
        if not self.current_section:
            self.start_section("Default Section")
            
        self.current_section["vulnerabilities"].append({
            "severity": severity,
            "description": description,
        })
        self.current_section["status"] = "FAILED"
        self.overall_status = "FAILED"

    def generate(self) -> str:
        """Generate the consolidated HTML report."""
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds() * 1000
        
        env = Environment(loader=FileSystemLoader(str(self.template_dir)))
        template = env.get_template("report_template.html")
        
        total_requests = 0
        passed_requests = 0
        for section in self.sections:
            sec_reqs = section["requests"]
            total_requests += len(sec_reqs)
            passed_requests += sum(1 for r in sec_reqs if r["status"] == "PASSED")
            
        failed_requests = total_requests - passed_requests
        
        html_content = template.render(
            suite_name=self.suite_name,
            timestamp=self.timestamp,
            overall_status=self.overall_status,
            total_tests=len(self.sections),
            total_requests=total_requests,
            passed_requests=passed_requests,
            failed_requests=failed_requests,
            duration_ms=int(duration),
            sections=self.sections,
        )
        
        filename = f"security_audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report_path = self.report_dir / filename
        
        with open(report_path, "w") as f:
            f.write(html_content)
            
        return str(report_path)
