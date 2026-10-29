"""retake requests

Revision ID: 1a2b3c4d5e6f
Revises: 8f3a1c5d9b27
Create Date: 2026-09-29 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, None] = '8f3a1c5d9b27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'retake_requests',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('participant_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('admin_note', sa.Text(), nullable=True),
        sa.Column('decided_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['participant_id'], ['participants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['decided_by'], ['admins.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status in ('pending','approved','rejected','used')",
                            name='ck_retake_request_status'),
    )
    op.create_index('ix_retake_requests_participant_status', 'retake_requests',
                     ['participant_id', 'status'])


def downgrade() -> None:
    op.drop_index('ix_retake_requests_participant_status', table_name='retake_requests')
    op.drop_table('retake_requests')
