"""软删除：所有表增加 del 标记列

Revision ID: c1d2e3f4a5b6
Revises: 2b3c4d5e6f7a
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = '2b3c4d5e6f7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 全量表清单（与 models/ 下的 8 张表一一对应）
TABLES = [
    'objects',
    'files',
    'relations',
    'users',
    'baselines',
    'baseline_items',
    'category_encoders',
    'category_attribute_defs',
]


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, 'is_deleted')
