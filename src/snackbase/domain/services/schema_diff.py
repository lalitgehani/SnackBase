"""Diff declared collection schemas against the live registry.

Used by ``POST /api/v1/migrations/plan`` and ``POST /api/v1/migrations/generate``.
This module is pure: it does not touch the database or the filesystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _by_name(schema: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in schema if item.get("name")}


def _type_of(item: dict[str, Any]) -> str:
    return str(item.get("type") or "").lower()


@dataclass
class SchemaPlan:
    """A declarative schema diff.

    ``added`` / ``removed`` / ``changed`` are the public response shape.
    """

    added: list[dict[str, Any]] = field(default_factory=list)
    removed: list[dict[str, Any]] = field(default_factory=list)
    changed: list[dict[str, Any]] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.changed)

    def has_destructive(self) -> bool:
        return any(
            item.get("destructive") for item in (*self.added, *self.removed, *self.changed)
        )

    def to_dict(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "added": list(self.added),
            "removed": list(self.removed),
            "changed": list(self.changed),
        }


def diff_collection_schemas(
    current: dict[str, list[dict[str, Any]]],
    declared: dict[str, list[dict[str, Any]]],
) -> SchemaPlan:
    """Compare live schemas to a declared set.

    Only collections named in ``declared`` are considered. Fields present in
    the live schema but missing from the declaration are removals. Field type
    changes, field removals, and unique-constraint additions are marked
    ``destructive: true``.
    """
    plan = SchemaPlan()

    for collection, declared_fields in declared.items():
        existing = current.get(collection)
        if existing is None:
            for item in declared_fields:
                plan.added.append(
                    {
                        "collection": collection,
                        "field": item.get("name"),
                        "type": _type_of(item),
                        "destructive": False,
                    }
                )
            continue

        exist_map = _by_name(existing)
        decl_map = _by_name(declared_fields)

        for fname, item in decl_map.items():
            if fname not in exist_map:
                plan.added.append(
                    {
                        "collection": collection,
                        "field": fname,
                        "type": _type_of(item),
                        "destructive": False,
                    }
                )
                continue

            old = exist_map[fname]
            old_type = _type_of(old)
            new_type = _type_of(item)
            if old_type != new_type:
                plan.changed.append(
                    {
                        "collection": collection,
                        "field": fname,
                        "from": old_type,
                        "to": new_type,
                        "destructive": True,
                    }
                )
            elif not old.get("unique") and item.get("unique"):
                plan.changed.append(
                    {
                        "collection": collection,
                        "field": fname,
                        "from": old_type,
                        "to": new_type,
                        "destructive": True,
                    }
                )

        for fname, item in exist_map.items():
            if fname not in decl_map:
                plan.removed.append(
                    {
                        "collection": collection,
                        "field": fname,
                        "type": _type_of(item),
                        "destructive": True,
                    }
                )

    return plan
