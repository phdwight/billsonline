"""remove include_in_internet

Revision ID: 7c2b1a4f1e3b
Revises: 189d01f76a08
Create Date: 2025-10-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c2b1a4f1e3b'
down_revision = '189d01f76a08'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the include_in_internet column from participants
    with op.batch_alter_table('participants', schema=None) as batch_op:
        try:
            batch_op.drop_column('include_in_internet')
        except Exception:
            # If the column doesn't exist (already removed), ignore
            pass


def downgrade():
    # Recreate the include_in_internet column (defaults to True)
    with op.batch_alter_table('participants', schema=None) as batch_op:
        batch_op.add_column(sa.Column('include_in_internet', sa.Boolean(), nullable=False, server_default=sa.text('1')))
    # Remove server default after backfill to keep schema tidy
    with op.batch_alter_table('participants', schema=None) as batch_op:
        batch_op.alter_column('include_in_internet', server_default=None)
