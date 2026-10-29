"""participant email

Revision ID: 8f3a1c5d9b27
Revises: d72faf97ddb9
Create Date: 2026-09-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f3a1c5d9b27'
down_revision: Union[str, None] = 'd72faf97ddb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: peserta lama tidak punya email. Peserta baru wajib mengisi lewat API.
    op.add_column('participants', sa.Column('email', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('participants', 'email')
