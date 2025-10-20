"""add distribution column to bill_components

Revision ID: cccccccccccc
Revises: b7e8e1c4d1f0
Create Date: 2025-10-20 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cccccccccccc'
down_revision = 'b7e8e1c4d1f0'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table('bill_components'):
        cols = [c.get('name') if isinstance(c, dict) else c['name'] for c in insp.get_columns('bill_components')]
        if 'distribution' not in cols:
            op.add_column('bill_components', sa.Column('distribution', sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table('bill_components'):
        cols = [c.get('name') if isinstance(c, dict) else c['name'] for c in insp.get_columns('bill_components')]
        if 'distribution' in cols:
            op.drop_column('bill_components', 'distribution')
