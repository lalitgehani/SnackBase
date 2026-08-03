"""Unit tests for function concurrency limiter and nested invoke budget."""

from snackbase.infrastructure.functions.concurrency import FunctionConcurrencyLimiter
from snackbase.infrastructure.functions.nested_budget import NestedInvokeBudget


def test_per_account_cap() -> None:
    limiter = FunctionConcurrencyLimiter(per_account=2, global_limit=10)
    assert limiter.try_acquire("a")
    assert limiter.try_acquire("a")
    assert not limiter.try_acquire("a")
    limiter.release("a")
    assert limiter.try_acquire("a")


def test_global_cap() -> None:
    limiter = FunctionConcurrencyLimiter(per_account=10, global_limit=2)
    assert limiter.try_acquire("a")
    assert limiter.try_acquire("b")
    assert not limiter.try_acquire("c")
    limiter.release("a")
    assert limiter.try_acquire("c")


def test_nested_budget_root_unlimited() -> None:
    budget = NestedInvokeBudget(limit_per_minute=2)
    assert budget.check_and_increment("root", 0)
    assert budget.check_and_increment("root", 0)
    assert budget.check_and_increment("root", 0)


def test_nested_budget_depth_limited() -> None:
    budget = NestedInvokeBudget(limit_per_minute=2)
    assert budget.check_and_increment("root", 1)
    assert budget.check_and_increment("root", 1)
    assert not budget.check_and_increment("root", 1)
