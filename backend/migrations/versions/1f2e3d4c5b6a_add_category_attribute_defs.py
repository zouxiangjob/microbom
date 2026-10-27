"""add category attribute defs

Revision ID: 1f2e3d4c5b6a
Revises: 92198316e659
Create Date: 2026-10-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f2e3d4c5b6a'
down_revision: Union[str, Sequence[str], None] = '92198316e659'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建分类属性定义专用表。"""
    op.create_table('category_attribute_defs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('category_id', sa.Uuid(), nullable=False),
        sa.Column('attr_key', sa.String(length=100), nullable=False),
        sa.Column('attr_label', sa.String(length=100), nullable=False),
        sa.Column('value_type', sa.String(length=20), nullable=False),
        sa.Column('required', sa.Boolean(), nullable=False),
        sa.Column('default_value', sa.JSON(), nullable=True),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_category_attribute_defs_category_id'), 'category_attribute_defs', ['category_id'], unique=False)


def downgrade() -> None:
    """删除分类属性定义表。"""
    op.drop_index(op.f('ix_category_attribute_defs_category_id'), table_name='category_attribute_defs')
    op.drop_table('category_attribute_defs')
