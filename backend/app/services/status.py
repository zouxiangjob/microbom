"""
生命周期状态机：状态枚举 + 合法转移。
"""

# 状态枚举
STATUS_DRAFT = "draft"        # 草稿
STATUS_REVIEW = "review"      # 待审核
STATUS_RELEASED = "released"  # 已发布
STATUS_ARCHIVED = "archived"  # 已归档

ALL_STATUSES = {STATUS_DRAFT, STATUS_REVIEW, STATUS_RELEASED, STATUS_ARCHIVED}

# 合法状态转移表：draft→review→released→archived，review 可打回 draft
STATUS_TRANSITIONS = {
    STATUS_DRAFT: {STATUS_REVIEW},
    STATUS_REVIEW: {STATUS_RELEASED, STATUS_DRAFT},
    STATUS_RELEASED: {STATUS_ARCHIVED},
    STATUS_ARCHIVED: set(),
}


def is_valid_status(status: str) -> bool:
    """是否为合法状态枚举值。"""
    return status in ALL_STATUSES


def validate_transition(from_status: str, to_status: str) -> bool:
    """校验 from_status -> to_status 是否为合法转移。"""
    if not is_valid_status(to_status):
        return False
    return to_status in STATUS_TRANSITIONS.get(from_status, set())
