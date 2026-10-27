"""
分类编码器载荷校验与编码生成的纯函数单测。
"""
import pytest

from app.services.category_encoder import (
    validate_encoder_payload,
    generate_sequence_code,
    execute_script,
)


# ── 校验 ──

def test_valid_sequence_encoder():
    assert validate_encoder_payload("sequence", "WD-", 1, 9999, 4, None) is None


def test_valid_script_encoder():
    assert validate_encoder_payload("script", None, None, None, None, "result = 'X'") is None


def test_invalid_type_rejected():
    msg = validate_encoder_payload("bogus", None, None, None, None, None)
    assert msg is not None and "bogus" in msg


def test_sequence_requires_start_seq():
    assert validate_encoder_payload("sequence", "WD-", None, 9999, 4, None) is not None


def test_sequence_end_less_than_start_rejected():
    assert validate_encoder_payload("sequence", "WD-", 10, 5, 4, None) is not None


def test_script_requires_script():
    assert validate_encoder_payload("script", None, None, None, None, "") is not None
    assert validate_encoder_payload("script", None, None, None, None, None) is not None


# ── 顺序编码生成 ──

def test_first_sequence_code():
    code, seq = generate_sequence_code("WD-", "", 1, 9999, 4, None)
    assert code == "WD-0001"
    assert seq == 1


def test_next_sequence_code():
    code, seq = generate_sequence_code("WD-", "-A", 1, 9999, 3, 42)
    assert code == "WD-043-A"
    assert seq == 43


def test_sequence_exhausted_raises():
    with pytest.raises(ValueError):
        generate_sequence_code("WD-", "", 1, 5, 4, 5)


# ── 脚本编码生成 ──

def test_script_executes_and_returns_result():
    code = execute_script("result = f'P-{latest_code or 1}'", None)
    assert code == "P-1"


def test_script_uses_latest_code():
    code = execute_script("result = f'X-{int(latest_code or 0) + 1}'", "5")
    assert code == "X-6"


def test_script_without_result_raises():
    with pytest.raises(ValueError):
        execute_script("x = 1", None)
