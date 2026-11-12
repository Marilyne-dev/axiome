"""paiements : offre visée (changement d'offre)

Revision ID: c91d5a7e2b40
Revises: 4f0b30c1e296
Create Date: 2026-11-12 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c91d5a7e2b40'
down_revision: Union[str, Sequence[str], None] = '4f0b30c1e296'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('paiements') as batch:
        batch.add_column(sa.Column('plan_id', sa.Integer(), nullable=True))
        batch.create_foreign_key('fk_paiements_plan_id', 'plans', ['plan_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('paiements') as batch:
        batch.drop_constraint('fk_paiements_plan_id', type_='foreignkey')
        batch.drop_column('plan_id')
