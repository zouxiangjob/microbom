"""add category encoders

Revision ID: 2b3c4d5e6f7a
Revises: 1f2e3d4c5b6a
Create Date: 2026-10-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b3c4d5e6f7a'
down_revision: Union[str, Sequence[str], None] = '1f2e3d4c5b6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建分类编码器专用表。"""
    op.create_table('category_encoders',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('category_id', sa.Uuid(), nullable=False),
        sa.Column('encoder_type', sa.String(length=20), nullable=False),
        sa.Column('prefix', sa.String(length=50), nullable=True),
        sa.Column('suffix', sa.String(length=50), nullable=True),
        sa.Column('start_seq', sa.Integer(), nullable=True),
        sa.Column('end_seq', sa.Integer(), nullable=True),
        sa.Column('seq_length', sa.Integer(), nullable=True),
        sa.Column('encoder_script', sa.Text(), nullable=True),
        sa.Column('current_seq', sa.Integer(), nullable=True),
        sa.Column('latest_code', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_category_encoders_category_id'), 'category_encoders', ['category_id'], unique=True)


def downgrade() -> None:
    """删除分类编码器表。"""
    op.drop_index(op.f('ix_category_encoders_category_id'), table_name='category_encoders')
    op.drop_table('category_encoders')
