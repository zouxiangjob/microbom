"""
图谱引擎纯函数单测：搜索字段解析、关键字段校验、CTE 平铺转嵌套。
"""
from app.services.graph import (
    AsyncGraphCrudEngine,
    _resolve_searchable_fields,
    cte_flat_to_nested_tree,
)

# validate_required_fields 是 AsyncGraphCrudEngine 的静态方法，此处取别名便于直接调用
validate_required_fields = AsyncGraphCrudEngine.validate_required_fields


def test_resolve_part_fields():
    fields = _resolve_searchable_fields("part")
    assert "part_number" in fields
    assert "name" in fields
    assert "material" in fields


def test_resolve_unknown_type_falls_back_to_default():
    assert _resolve_searchable_fields("bogus") == ["part_number", "name"]


def test_resolve_none_returns_union_deduped():
    fields = _resolve_searchable_fields(None)
    # 并集应包含各类型的字段，且无重复
    assert len(fields) == len(set(fields))
    assert "part_number" in fields
    assert "name" in fields
    assert "tag" in fields  # document 专属字段


def test_required_fields_part_missing():
    msg = validate_required_fields("part", {})
    assert msg is not None and "part_number" in msg


def test_required_fields_part_blank():
    assert validate_required_fields("part", {"part_number": "   "}) is not None
    assert validate_required_fields("part", {"part_number": ""}) is not None


def test_required_fields_ok():
    assert validate_required_fields("part", {"part_number": "P-001"}) is None
    assert validate_required_fields("document", {"name": "工艺卡"}) is None


def test_required_fields_unknown_type_no_requirement():
    assert validate_required_fields("bogus", {}) is None


def test_cte_flat_to_nested_tree():
    flat = [
        {
            "edge": {"source_id": "root-1", "target_id": "child-1"},
            "target_node": {"id": "child-1", "properties": {"part_number": "P1"}},
        },
        {
            "edge": {"source_id": "child-1", "target_id": "grand-1"},
            "target_node": {"id": "grand-1", "properties": {"name": "G1"}},
        },
        {
            "edge": {"source_id": "root-1", "target_id": "child-2"},
            "target_node": {"id": "child-2", "properties": {"part_number": "P2"}},
        },
    ]
    tree = cte_flat_to_nested_tree(flat, "root-1")
    assert len(tree) == 2

    child1 = next(n for n in tree if n["id"] == "child-1")
    assert child1["label"] == "P1"
    assert child1["children"] == [{"id": "grand-1", "label": "G1", "children": []}]

    child2 = next(n for n in tree if n["id"] == "child-2")
    assert child2["label"] == "P2"
    assert child2["children"] == []
