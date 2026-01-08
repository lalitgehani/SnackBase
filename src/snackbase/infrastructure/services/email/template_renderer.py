"""Jinja2 template renderer for email templates.

Provides safe template rendering with HTML escaping and error handling.
"""

from jinja2 import Environment, Template, TemplateSyntaxError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment

from snackbase.core.logging import get_logger

logger = get_logger(__name__)


class TemplateRenderer:
    """Jinja2 template renderer with security features.

    Uses sandboxed environment to prevent code execution in templates.
    """

    def __init__(self) -> None:
        """Initialize the template renderer with sandboxed environment."""
        self.env = SandboxedEnvironment(
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_string: str, variables: dict[str, str]) -> str:
        """Render a template string with variables.

        Args:
            template_string: Jinja2 template string.
            variables: Dictionary of variables to substitute.

        Returns:
            Rendered template string.

        Raises:
            TemplateSyntaxError: If template syntax is invalid.
            UndefinedError: If required variable is missing.
        """
        try:
            template = self.env.from_string(template_string)
            rendered = template.render(**variables)
            logger.debug("Template rendered successfully", variable_count=len(variables))
            return rendered
        except TemplateSyntaxError as e:
            logger.error("Template syntax error", error=str(e), line=e.lineno)
            raise
        except UndefinedError as e:
            logger.error("Undefined variable in template", error=str(e))
            raise
        except Exception as e:
            logger.error("Template rendering failed", error=str(e))
            raise


# Global template renderer instance
_template_renderer: TemplateRenderer | None = None


def get_template_renderer() -> TemplateRenderer:
    """Get the global template renderer instance.

    Returns:
        TemplateRenderer: Global template renderer instance.
    """
    global _template_renderer
    if _template_renderer is None:
        _template_renderer = TemplateRenderer()
    return _template_renderer
