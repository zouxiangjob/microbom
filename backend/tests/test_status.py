"""
生命周期状态机纯函数单测：状态枚举与合法转移表。
"""
from app.services.status import (
    STATUS_DRAFT,
    STATUS_REVIEW,
    STATUS_RELEASED,
    STATUS_ARCHIVED,
    is_valid_status,
    validate_transition,
)


def test_valid_statuses():
    assert is_valid_status("draft") is True
    assert is_valid_status("review") is True
    assert is_valid_status("released") is True
    assert is_valid_status("archived") is True


def test_invalid_statuses():
    assert is_valid_status("foo") is False
    assert is_valid_status("") is False
    assert is_valid_status("DRAFT") is False  # 大小写敏感


def test_forward_transitions():
    assert validate_transition(STATUS_DRAFT, STATUS_REVIEW) is True
    assert validate_transition(STATUS_REVIEW, STATUS_RELEASED) is True
    assert validate_transition(STATUS_RELEASED, STATUS_ARCHIVED) is True


def test_review_can_reject_to_draft():
    assert validate_transition(STATUS_REVIEW, STATUS_DRAFT) is True


def test_illegal_transitions():
    assert validate_transition(STATUS_DRAFT, STATUS_RELEASED) is False
    assert validate_transition(STATUS_DRAFT, STATUS_ARCHIVED) is False
    assert validate_transition(STATUS_RELEASED, STATUS_DRAFT) is False
    assert validate_transition(STATUS_ARCHIVED, STATUS_DRAFT) is False  # archived 无出边
    assert validate_transition(STATUS_ARCHIVED, STATUS_RELEASED) is False


def test_transition_to_invalid_target():
    assert validate_transition(STATUS_DRAFT, "bogus") is False
