"""add redistribution fields

Revision ID: 9f3c2c7d2a10
Revises: 7c2b1a4f1e3b
Create Date: 2025-10-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f3c2c7d2a10'
down_revision = '7c2b1a4f1e3b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('monthly_adjustments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('redis_electricity', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('redis_water', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('redis_internet', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('monthly_adjustments', schema=None) as batch_op:
        batch_op.drop_column('redis_internet')
        batch_op.drop_column('redis_water')
        batch_op.drop_column('redis_electricity')
