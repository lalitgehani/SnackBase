"""Unit tests for Permission domain entity."""

import pytest

from snackbase.domain.entities.permission import (
    OperationRule,
    Permission,
    PermissionRules,
)


def test_operation_rule_validation():
    """Test OperationRule validation."""
    # Valid rule
    rule = OperationRule(rule="true", fields="*")
    assert rule.rule == "true"
    assert rule.fields == "*"

    # Valid rule with fields list
    rule = OperationRule(rule="true", fields=["id", "name"])
    assert rule.fields == ["id", "name"]

    # Invalid rule: empty expression
    with pytest.raises(ValueError, match="Rule expression is required"):
        OperationRule(rule="", fields="*")

    # Invalid rule: fields not list or "*"
    with pytest.raises(ValueError, match=r"Fields must be '\*' or a list of field names"):
        OperationRule(rule="true", fields="invalid")  # type: ignore


def test_permission_rules_serialization():
    """Test PermissionRules to_dict and from_dict."""
    rules = PermissionRules(
        create=OperationRule(rule="true", fields="*"),
        read=OperationRule(rule="user.id == record.owner_id", fields=["id", "title"]),
    )

    # to_dict
    data = rules.to_dict()
    assert data["create"] == {"rule": "true", "fields": "*"}
    assert data["read"] == {
        "rule": "user.id == record.owner_id",
        "fields": ["id", "title"],
    }
    assert "update" not in data
    assert "delete" not in data

    # from_dict
    restored = PermissionRules.from_dict(data)
    assert restored.create.rule == "true"
    assert restored.create.fields == "*"
    assert restored.read.rule == "user.id == record.owner_id"
    assert restored.read.fields == ["id", "title"]
    assert restored.update is None
    assert restored.delete is None


def test_permission_validation():
    """Test Permission entity validation."""
    rules = PermissionRules(read=OperationRule(rule="true"))

    # Valid permission
    perm = Permission(role_id=1, collection="posts", rules=rules)
    assert perm.collection == "posts"

    # Invalid permission: empty collection
    with pytest.raises(ValueError, match="Collection name is required"):
        Permission(role_id=1, collection="", rules=rules)

    # Invalid permission: invalid role_id
    with pytest.raises(ValueError, match="Role ID must be a positive integer"):
        Permission(role_id=0, collection="posts", rules=rules)
