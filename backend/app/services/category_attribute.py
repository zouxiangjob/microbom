"""
分类属性定义服务：专用表 CRUD 与载荷校验。
"""
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category_attribute import CategoryAttributeDef

# 合法属性类型
VALUE_TYPES = {"string", "number", "boolean", "enum", "date", "text"}


def validate_attr_payload(value_type: str, options: Optional[List[str]]) -> Optional[str]:
    """校验属性定义载荷，返回错误信息；通过返回 None。"""
    if value_type not in VALUE_TYPES:
        return f"非法属性类型 [{value_type}]，可选值: {', '.join(sorted(VALUE_TYPES))}"
    if value_type == "enum" and (not options):
        return "enum 类型必须提供非空的 options 候选值"
    return None


async def create_attr_def(
        db: AsyncSession,
        *,
        category_id: uuid.UUID,
        attr_key: str,
        attr_label: str,
        value_type: str = "string",
        required: bool = False,
        default_value: Optional[Any] = None,
        options: Optional[List[str]] = None,
        unit: Optional[str] = None,
        sort_order: int = 0,
) -> CategoryAttributeDef:
    """为某分类新增一条属性定义。"""
    defn = CategoryAttributeDef(
        category_id=category_id,
        attr_key=attr_key,
        attr_label=attr_label,
        value_type=value_type,
        required=required,
        default_value=default_value,
        options=options,
        unit=unit,
        sort_order=sort_order,
    )
    db.add(defn)
    await db.commit()
    await db.refresh(defn)
    return defn


async def list_attr_defs(db: AsyncSession, category_id: uuid.UUID) -> List[CategoryAttributeDef]:
    """按分类查询其全部属性定义，按 sort_order 排序。"""
    stmt = (
        select(CategoryAttributeDef)
        .where(CategoryAttributeDef.category_id == category_id)
        .order_by(CategoryAttributeDef.sort_order, CategoryAttributeDef.created_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_attr_def(db: AsyncSession, attr_id: uuid.UUID) -> Optional[CategoryAttributeDef]:
    """按 ID 查询单条属性定义。"""
    return await db.get(CategoryAttributeDef, attr_id)


async def update_attr_def(
        db: AsyncSession,
        attr_id: uuid.UUID,
        updates: Dict[str, Any],
) -> CategoryAttributeDef:
    """增量更新属性定义；合并后重新校验，非法则抛 ValueError。"""
    defn = await db.get(CategoryAttributeDef, attr_id)
    if not defn:
        raise ValueError(f"属性定义 [{attr_id}] 不存在")

    # 合并后校验：value_type 与 options 取「更新值或当前值」
    merged_type = updates.get("value_type", defn.value_type)
    merged_options = updates.get("options", defn.options)
    err = validate_attr_payload(merged_type, merged_options)
    if err:
        raise ValueError(err)

    for key, value in updates.items():
        if value is not None:
            setattr(defn, key, value)

    await db.commit()
    await db.refresh(defn)
    return defn


async def delete_attr_def(db: AsyncSession, attr_id: uuid.UUID) -> bool:
    """删除单条属性定义，成功返回 True，不存在返回 False。"""
    defn = await db.get(CategoryAttributeDef, attr_id)
    if not defn:
        return False
    await db.delete(defn)
    await db.commit()
    return True
