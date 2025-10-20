"""add tables for dynamic bill components

Revision ID: b7e8e1c4d1f0
Revises: 9f3c2c7d2a10
Create Date: 2025-10-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7e8e1c4d1f0'
down_revision = '9f3c2c7d2a10'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table('bill_components'):
        op.create_table(
            'bill_components',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('month_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=64), nullable=False),
            sa.Column('amount', sa.Float(), nullable=False, server_default='0'),
            sa.Column('split_method', sa.String(length=16), nullable=False, server_default='equal'),
            sa.Column('distribution', sa.JSON(), nullable=True),
            sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['month_id'], ['monthly_bills.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('month_id', 'name', name='uq_component_month_name')
        )
        try:
            op.create_index(op.f('ix_bill_components_month_id'), 'bill_components', ['month_id'], unique=False)
        except Exception:
            pass

    if not insp.has_table('component_adjustments'):
        op.create_table(
            'component_adjustments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('month_id', sa.Integer(), nullable=False),
            sa.Column('component_id', sa.Integer(), nullable=False),
            sa.Column('participant_id', sa.Integer(), nullable=False),
            sa.Column('zero', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('redis_rule', sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(['component_id'], ['bill_components.id'], ),
            sa.ForeignKeyConstraint(['month_id'], ['monthly_bills.id'], ),
            sa.ForeignKeyConstraint(['participant_id'], ['participants.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('month_id', 'component_id', 'participant_id', name='uq_component_adj_triplet')
        )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table('component_adjustments'):
        op.drop_table('component_adjustments')
    try:
        op.drop_index(op.f('ix_bill_components_month_id'), table_name='bill_components')
    except Exception:
        pass
    if insp.has_table('bill_components'):
        op.drop_table('bill_components')
