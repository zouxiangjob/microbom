"""
版本号序列（A→Z→AA→AB）与基线条目对比的纯函数单测。
"""
from app.services.baseline import (
    _version_to_seq,
    _seq_to_version,
    _safe_qty,
    _part_number,
    _compare_items,
)


def test_version_to_seq_boundaries():
    assert _version_to_seq("A") == 1
    assert _version_to_seq("B") == 2
    assert _version_to_seq("Z") == 26
    assert _version_to_seq("AA") == 27
    assert _version_to_seq("AB") == 28
    assert _version_to_seq("AZ") == 52
    assert _version_to_seq("BA") == 53
    assert _version_to_seq("ZZ") == 702
    assert _version_to_seq("AAA") == 703


def test_seq_to_version_boundaries():
    assert _seq_to_version(1) == "A"
    assert _seq_to_version(2) == "B"
    assert _seq_to_version(26) == "Z"
    assert _seq_to_version(27) == "AA"
    assert _seq_to_version(28) == "AB"
    assert _seq_to_version(52) == "AZ"
    assert _seq_to_version(53) == "BA"
    assert _seq_to_version(702) == "ZZ"
    assert _seq_to_version(703) == "AAA"


def test_version_roundtrip():
    for seq in range(1, 1000):
        assert _version_to_seq(_seq_to_version(seq)) == seq


def test_version_to_seq_tolerates_case_and_garbage():
    assert _version_to_seq("a") == 1  # 小写转大写
    assert _version_to_seq(" a ") == 1  # 去空白
    assert _version_to_seq("A1") == 1  # 非字母忽略
    assert _version_to_seq("") == 0


def test_seq_to_version_zero_is_empty():
    assert _seq_to_version(0) == ""


def test_safe_qty():
    assert _safe_qty(None) is None
    assert _safe_qty("3") == 3
    assert _safe_qty(5) == 5
    assert _safe_qty("abc") == 1
    assert _safe_qty(3.7) == 3


def test_part_number_priority():
    assert _part_number(None) == ""
    assert _part_number({}) == ""
    assert _part_number({"part_number": "X"}) == "X"
    assert _part_number({"name": "Y"}) == "Y"
    assert _part_number({"part_number": "X", "name": "Y"}) == "X"


def _item(**overrides):
    """构造一条完整的冻结条目字典，便于 _compare_items 测试。"""
    base = {
        "object_id": "obj-1",
        "object_type": "part",
        "relation_type": "bom_relation",
        "properties": {"part_number": "P1"},
        "parent_object_id": "parent-1",
        "depth": 1,
        "quantity": 2,
        "edge_properties": {"quantity": 2, "position": "01"},
    }
    base.update(overrides)
    return base


def test_compare_items_no_change():
    assert _compare_items(_item(), _item()) == []


def test_compare_items_quantity_change():
    changes = _compare_items(_item(), _item(quantity=3))
    fields = {c["field"] for c in changes}
    assert "quantity" in fields
    q = next(c for c in changes if c["field"] == "quantity")
    assert q["from"] == 2 and q["to"] == 3


def test_compare_items_parent_change():
    changes = _compare_items(_item(), _item(parent_object_id="parent-2"))
    assert any(c["field"] == "parent_object_id" for c in changes)


def test_compare_items_properties_change():
    changes = _compare_items(_item(), _item(properties={"part_number": "P2"}))
    assert any(c["field"] == "properties" for c in changes)


def test_compare_items_edge_properties_change_excludes_quantity():
    # 仅 position 变化、quantity 相同 → 上报 edge_properties 变更（quantity 已被剥离）
    changes = _compare_items(_item(), _item(edge_properties={"quantity": 2, "position": "02"}))
    assert any(c["field"] == "edge_properties" for c in changes)
