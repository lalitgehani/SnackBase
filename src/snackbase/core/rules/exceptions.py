"""Exceptions for rule parsing and evaluation."""

class RuleError(Exception):
    """Base class for all rule-related errors."""
    pass

class RuleSyntaxError(RuleError):
    """Raised when rule syntax is invalid."""
    def __init__(self, message: str, position: int | None = None):
        self.position = position
        super().__init__(f"{message} at position {position}" if position is not None else message)

class RuleEvaluationError(RuleError):
    """Raised when rule evaluation fails."""
    pass
