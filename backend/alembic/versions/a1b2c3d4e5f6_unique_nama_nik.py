"""unique nama dan nik peserta

Revision ID: a1b2c3d4e5f6
Revises: 9c1d2e3f4a5b
"""
from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9c1d2e3f4a5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_participants_nama ON participants (lower(btrim(nama)))")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_participants_nik ON participants (nik) WHERE nik IS NOT NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_participants_nik")
    op.execute("DROP INDEX IF EXISTS uq_participants_nama")
