"""add_notes_to_component_adjustments

Revision ID: 55798fa759fc
Revises: cccccccccccc
Create Date: 2026-01-15 09:40:45.233639

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '55798fa759fc'
down_revision = 'cccccccccccc'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('component_adjustments', sa.Column('notes', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('component_adjustments', 'notes')
