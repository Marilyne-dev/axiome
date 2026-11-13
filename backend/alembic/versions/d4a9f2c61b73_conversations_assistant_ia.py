"""conversations de l'assistant IA

Revision ID: d4a9f2c61b73
Revises: c91d5a7e2b40
Create Date: 2026-11-13 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4a9f2c61b73'
down_revision: Union[str, Sequence[str], None] = 'c91d5a7e2b40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('ia_conversations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('titre', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('ia_conversations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ia_conversations_user_id'), ['user_id'], unique=False)

    op.create_table('ia_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=10), nullable=False),
    sa.Column('contenu', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['ia_conversations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('ia_messages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ia_messages_conversation_id'), ['conversation_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('ia_messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ia_messages_conversation_id'))
    op.drop_table('ia_messages')
    with op.batch_alter_table('ia_conversations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ia_conversations_user_id'))
    op.drop_table('ia_conversations')
