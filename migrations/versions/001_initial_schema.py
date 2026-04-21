"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables."""
    op.create_table(
        'tts_requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('text_hash', sa.String(64), nullable=False),
        sa.Column('engine', sa.String(50), nullable=False),
        sa.Column('voice', sa.String(100), nullable=False),
        sa.Column('rate', sa.Float(), nullable=False, default=1.0),
        sa.Column('volume', sa.Float(), nullable=False, default=1.0),
        sa.Column('pitch', sa.Float(), nullable=False, default=1.0),
        sa.Column('format', sa.String(10), nullable=False),
        sa.Column('audio_path', sa.String(500), nullable=True),
        sa.Column('cache_key', sa.String(64), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Float(), nullable=False),
        sa.Column('cached', sa.Boolean(), nullable=False, default=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    
    # Create indexes
    op.create_index('ix_tts_requests_text_hash', 'tts_requests', ['text_hash'])
    op.create_index('ix_tts_requests_engine', 'tts_requests', ['engine'])
    op.create_index('ix_tts_requests_cache_key', 'tts_requests', ['cache_key'])
    op.create_index('ix_tts_requests_cached', 'tts_requests', ['cached'])
    op.create_index('ix_tts_requests_status', 'tts_requests', ['status'])
    op.create_index('ix_tts_requests_created_at', 'tts_requests', ['created_at'])


def downgrade() -> None:
    """Drop initial tables."""
    op.drop_table('tts_requests')
