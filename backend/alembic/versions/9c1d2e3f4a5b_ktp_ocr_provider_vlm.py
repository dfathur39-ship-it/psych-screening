"""ktp ocr provider columns (vlm)

Revision ID: 9c1d2e3f4a5b
Revises: 1a2b3c4d5e6f
Create Date: 2026-10-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9c1d2e3f4a5b'
down_revision: Union[str, None] = '1a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ktp_documents', sa.Column('ocr_provider', sa.String(length=20), nullable=True))
    op.add_column('ktp_documents', sa.Column('ocr_fallback_used', sa.Boolean(), nullable=False, server_default='false'))
    op.execute("UPDATE ktp_documents SET ocr_provider = 'tesseract' WHERE ocr_provider IS NULL")
    op.execute("UPDATE ktp_documents SET ocr_fallback_used = false WHERE ocr_fallback_used IS NULL")
    op.alter_column('ktp_documents', 'ocr_fallback_used', server_default=None)


def downgrade() -> None:
    op.drop_column('ktp_documents', 'ocr_fallback_used')
    op.drop_column('ktp_documents', 'ocr_provider')
