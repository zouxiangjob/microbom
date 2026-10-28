"""
分类编码器服务：专用表 CRUD、载荷校验与编码生成。
"""
import datetime
import random
import time
import uuid
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category_encoder import CategoryEncoder

# 合法编码器类型
ENCODER_TYPES = {"sequence", "script"}


def validate_encoder_payload(
        encoder_type: str,
        prefix: Optional[str],
        start_seq: Optional[int],
        end_seq: Optional[int],
        seq_length: Optional[int],
        encoder_script: Optional[str],
) -> Optional[str]:
    """校验编码器载荷，返回错误信息；通过返回 None。"""
    if encoder_type not in ENCODER_TYPES:
        return f"非法编码器类型 [{encoder_type}]，可选值: {', '.join(sorted(ENCODER_TYPES))}"
    if encoder_type == "sequence":
        if start_seq is None:
            return "顺序编码器必须提供 start_seq（起始流水）"
        if end_seq is not None and end_seq < start_seq:
            return "终止流水 end_seq 不能小于起始流水 start_seq"
        if seq_length is not None and seq_length <= 0:
            return "seq_length（流水码位数）必须为正整数"
    else:  # script
        if not encoder_script or not encoder_script.strip():
            return "脚本编码器必须提供 encoder_script"
    return None


def generate_sequence_code(
        prefix: Optional[str],
        suffix: Optional[str],
        start_seq: int,
        end_seq: Optional[int],
        seq_length: Optional[int],
        current_seq: Optional[int],
) -> Tuple[str, int]:
    """纯函数：计算下一个顺序编码，返回 (新编码, 下一流水号)；耗尽时抛 ValueError。"""
    next_seq = start_seq if current_seq is None else current_seq + 1
    if end_seq is not None and next_seq > end_seq:
        raise ValueError(f"流水号已用尽：下一号 {next_seq} 超过终止流水 {end_seq}")
    seq_str = str(next_seq).zfill(seq_length or 0)
    code = f"{prefix or ''}{seq_str}{suffix or ''}"
    return code, next_seq


def execute_script(script: str, latest_code: Optional[str]) -> str:
    """纯函数：执行方式2自定义脚本，脚本须通过给 result 赋值返回新编码字符串。"""
    namespace: Dict[str, Any] = {
        "latest_code": latest_code,
        "datetime": datetime,
        "time": time,
        "uuid": uuid,
        "random": random,
        "result": None,
    }
    # 安全提示：此函数执行任意 Python 代码，仅限可信管理员配置脚本时使用。
    exec(script, namespace)  # nosec B102
    result = namespace.get("result")
    if not isinstance(result, str) or not result.strip():
        raise ValueError("脚本必须通过给 result 变量赋值来返回非空字符串")
    return result.strip()


# ==============================================================================
# CRUD
# ==============================================================================

async def get_encoder_by_category(db: AsyncSession, category_id: uuid.UUID) -> Optional[CategoryEncoder]:
    """按分类节点 UUID 查询其编码器。"""
    stmt = select(CategoryEncoder).where(
        CategoryEncoder.category_id == category_id,
        CategoryEncoder.is_deleted == False,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_encoder(db: AsyncSession, **fields) -> CategoryEncoder:
    """为分类创建编码器；已存在则抛 ValueError（1:1）。"""
    existing = await get_encoder_by_category(db, fields["category_id"])
    if existing:
        raise ValueError(f"分类 [{fields['category_id']}] 已配置编码器，请使用更新接口")
    enc = CategoryEncoder(**fields)
    db.add(enc)
    await db.commit()
    await db.refresh(enc)
    return enc


async def update_encoder(db: AsyncSession, category_id: uuid.UUID, updates: Dict[str, Any]) -> CategoryEncoder:
    """增量更新编码器；合并后重新校验，非法或不存在则抛 ValueError。"""
    enc = await get_encoder_by_category(db, category_id)
    if not enc:
        raise ValueError(f"分类 [{category_id}] 未配置编码器")

    merged = {
        "encoder_type": updates.get("encoder_type", enc.encoder_type),
        "prefix": updates.get("prefix", enc.prefix),
        "start_seq": updates.get("start_seq", enc.start_seq),
        "end_seq": updates.get("end_seq", enc.end_seq),
        "seq_length": updates.get("seq_length", enc.seq_length),
        "encoder_script": updates.get("encoder_script", enc.encoder_script),
    }
    err = validate_encoder_payload(
        merged["encoder_type"], merged["prefix"], merged["start_seq"],
        merged["end_seq"], merged["seq_length"], merged["encoder_script"],
    )
    if err:
        raise ValueError(err)

    for key, value in updates.items():
        if value is not None:
            setattr(enc, key, value)

    await db.commit()
    await db.refresh(enc)
    return enc


async def delete_encoder(db: AsyncSession, category_id: uuid.UUID) -> bool:
    """软删除编码器，成功返回 True，不存在返回 False。"""
    enc = await get_encoder_by_category(db, category_id)
    if not enc:
        return False
    enc.is_deleted = True
    await db.commit()
    return True


async def generate_code(db: AsyncSession, category_id: uuid.UUID) -> str:
    """为分类生成下一个编码，更新跟踪字段并返回新编码。"""
    enc = await get_encoder_by_category(db, category_id)
    if not enc:
        raise ValueError(f"分类 [{category_id}] 未配置编码器")

    if enc.encoder_type == "sequence":
        code = await _next_sequence_code_atomic(db, enc)
    else:
        code = execute_script(enc.encoder_script, enc.latest_code)

    enc.latest_code = code
    await db.commit()
    await db.refresh(enc)
    return code


async def _next_sequence_code_atomic(db: AsyncSession, enc: CategoryEncoder) -> str:
    """原子递增流水号并生成编码，避免并发读-改-写导致的重复发号。

    将「读当前流水 + 加一」合并为单条 UPDATE ... RETURNING 原子写：多个并发请求在
    SQLite 单写者串行化下各自拿到唯一的流水号，而非先 SELECT 再 UPDATE 的竞态窗口。
    """
    start_seq = enc.start_seq
    # COALESCE(current_seq, start_seq - 1) + 1：首号从 start_seq 开始，之后每次 +1
    stmt = (
        update(CategoryEncoder)
        .where(CategoryEncoder.id == enc.id)
        .values(current_seq=func.coalesce(CategoryEncoder.current_seq, start_seq - 1) + 1)
        .returning(CategoryEncoder.current_seq)
    )
    next_seq = (await db.execute(stmt)).scalar_one()

    end_seq = enc.end_seq
    if end_seq is not None and next_seq > end_seq:
        # 超出终止流水：回滚本次递增，保持原流水不变（先缓存 end_seq，避免 rollback 后访问已过期属性）
        await db.rollback()
        raise ValueError(f"流水号已用尽：下一号 {next_seq} 超过终止流水 {end_seq}")

    seq_str = str(next_seq).zfill(enc.seq_length or 0)
    return f"{enc.prefix or ''}{seq_str}{enc.suffix or ''}"
