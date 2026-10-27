"""
分类属性定义载荷校验的纯函数单测。
"""
from app.services.category_attribute import validate_attr_payload, VALUE_TYPES


def test_all_declared_types_are_valid():
    for vt in VALUE_TYPES:
        options = ["A", "B"] if vt == "enum" else None
        assert validate_attr_payload(vt, options) is None


def test_invalid_type_rejected():
    msg = validate_attr_payload("unknown", None)
    assert msg is not None and "unknown" in msg


def test_enum_requires_options():
    assert validate_attr_payload("enum", None) is not None
    assert validate_attr_payload("enum", []) is not None
    assert validate_attr_payload("enum", ["A", "B"]) is None


def test_non_enum_without_options_is_ok():
    assert validate_attr_payload("string", None) is None
    assert validate_attr_payload("number", None) is None
    assert validate_attr_payload("boolean", None) is None
