"""
分类属性定义 API：为各分类配置其零部件应具备的属性模板。
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.database.session import get_db
from app.api.deps import require_roles
from app.schemas.category_attribute import (
    CategoryAttributeCreate,
    CategoryAttributeResponse,
    CategoryAttributeUpdate,
    PartAttributeSchemaResponse,
)
from app.services.category_attribute import (
    build_part_attribute_schema,
    create_attr_def,
    delete_attr_def,
    get_attr_def,
    list_attr_defs,
    update_attr_def,
    validate_attr_payload,
)

router = APIRouter()


@router.post("", response_model=CategoryAttributeResponse, status_code=status.HTTP_201_CREATED,
             summary="为分类新增属性定义")
async def create_category_attribute(
        payload: CategoryAttributeCreate,
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer")),
):
    """新增一条分类属性定义；enum 类型需提供 options 候选值。"""
    err = validate_attr_payload(payload.value_type, payload.options)
    if err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err)
    return await create_attr_def(db, **payload.model_dump())


@router.get("", response_model=List[CategoryAttributeResponse], summary="查询某分类的属性定义")
async def list_category_attributes(
        category_id: uuid.UUID = Query(..., description="分类对象 UUID"),
        db: AsyncSession = Depends(get_db),
):
    """返回某分类下按 sort_order 排序的全部属性定义。"""
    return await list_attr_defs(db, category_id)


@router.get("/part-schema/{part_id}", response_model=PartAttributeSchemaResponse,
            summary="聚合零件所属分类的属性定义与当前值")
async def get_part_attribute_schema(
        part_id: uuid.UUID = Path(..., description="零件节点 UUID"),
        db: AsyncSession = Depends(get_db),
):
    """反查零件分类 → 拉取该分类属性定义 → 合并当前 properties 值，供前端动态渲染属性清单。"""
    result = await build_part_attribute_schema(db, part_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="零件不存在或类型不是 part")
    return result


@router.put("/{attr_id}", response_model=CategoryAttributeResponse, summary="更新属性定义")
async def update_category_attribute(
        attr_id: uuid.UUID,
        payload: CategoryAttributeUpdate,
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer")),
):
    """增量更新属性定义，合并后重新校验类型与 options。"""
    try:
        return await update_attr_def(db, attr_id, payload.model_dump(exclude_unset=True))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))


@router.delete("/{attr_id}", summary="删除属性定义")
async def delete_category_attribute(
        attr_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer")),
):
    """删除单条属性定义。"""
    ok = await delete_attr_def(db, attr_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="属性定义不存在")
    return {"status": "success", "detail": f"属性定义 {attr_id} 已删除"}
