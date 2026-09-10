"""HookContext must import on Python 3.12/3.13 (TYPE_CHECKING-only names)."""

from __future__ import annotations

import ast
from pathlib import Path

from snackbase.domain.entities.hook_context import HookContext, HookResult

SRC = Path(__file__).resolve().parents[4] / "src" / "snackbase"


def test_hook_context_constructs_without_user_type():
    ctx = HookContext(app=object())
    assert ctx.user is None
    assert ctx.request is None
    assert ctx.request_id.startswith("hk_")
    result = HookResult(success=True)
    assert result.success is True


def _type_checking_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING"):
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.ImportFrom):
                for alias in stmt.names:
                    names.add(alias.asname or alias.name)
            elif isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    names.add(alias.asname or alias.name.split(".")[0])
    return names


def _annotation_uses_names(node: ast.AST, names: set[str]) -> bool:
    for attr in ("annotation", "returns"):
        ann = getattr(node, attr, None)
        if ann is None:
            continue
        for child in ast.walk(ann):
            if isinstance(child, ast.Name) and child.id in names:
                return True
    return False


def _has_future_annotations(tree: ast.AST) -> bool:
    return any(
        isinstance(n, ast.ImportFrom)
        and n.module == "__future__"
        and any(a.name == "annotations" for a in n.names)
        for n in tree.body
    )


def test_type_checking_annotation_names_are_quoted_or_postponed():
    """Bare TYPE_CHECKING names in annotations NameError on 3.12/3.13."""
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        source = path.read_text()
        if "TYPE_CHECKING" not in source:
            continue
        tree = ast.parse(source, filename=str(path))
        names = _type_checking_names(tree)
        if not names or _has_future_annotations(tree):
            continue
        for node in ast.walk(tree):
            if _annotation_uses_names(node, names):
                offenders.append(str(path.relative_to(SRC.parent)))
                break
    assert offenders == [], offenders
