"""Unit tests for the declarative schema diff engine."""

from snackbase.domain.services.schema_diff import diff_collection_schemas


def test_unchanged_schema_is_empty():
    schema = [{"name": "title", "type": "text"}]
    plan = diff_collection_schemas({"posts": schema}, {"posts": schema})
    assert plan.is_empty()
    assert plan.to_dict() == {"added": [], "removed": [], "changed": []}


def test_adding_nullable_text_is_not_destructive():
    current = {"posts": [{"name": "title", "type": "text"}]}
    declared = {
        "posts": [
            {"name": "title", "type": "text"},
            {"name": "subtitle", "type": "text"},
        ]
    }
    plan = diff_collection_schemas(current, declared)
    assert plan.added == [
        {
            "collection": "posts",
            "field": "subtitle",
            "type": "text",
            "destructive": False,
        }
    ]
    assert plan.changed == []
    assert plan.removed == []
    assert plan.has_destructive() is False


def test_text_to_number_is_destructive():
    current = {"posts": [{"name": "views", "type": "text"}]}
    declared = {"posts": [{"name": "views", "type": "number"}]}
    plan = diff_collection_schemas(current, declared)
    assert plan.changed == [
        {
            "collection": "posts",
            "field": "views",
            "from": "text",
            "to": "number",
            "destructive": True,
        }
    ]
    assert plan.has_destructive() is True


def test_reference_to_text_is_destructive():
    current = {
        "deals": [
            {"name": "company", "type": "reference", "collection": "companies"}
        ]
    }
    declared = {"deals": [{"name": "company", "type": "text"}]}
    plan = diff_collection_schemas(current, declared)
    assert plan.changed[0]["destructive"] is True
    assert plan.changed[0]["from"] == "reference"
    assert plan.changed[0]["to"] == "text"


def test_field_removal_is_destructive():
    current = {
        "posts": [
            {"name": "title", "type": "text"},
            {"name": "draft", "type": "boolean"},
        ]
    }
    declared = {"posts": [{"name": "title", "type": "text"}]}
    plan = diff_collection_schemas(current, declared)
    assert plan.removed == [
        {
            "collection": "posts",
            "field": "draft",
            "type": "boolean",
            "destructive": True,
        }
    ]


def test_unique_addition_is_destructive():
    current = {"posts": [{"name": "slug", "type": "text"}]}
    declared = {"posts": [{"name": "slug", "type": "text", "unique": True}]}
    plan = diff_collection_schemas(current, declared)
    assert len(plan.changed) == 1
    assert plan.changed[0]["destructive"] is True
