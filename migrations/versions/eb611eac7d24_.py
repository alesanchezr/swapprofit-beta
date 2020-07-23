"""empty message

Revision ID: eb611eac7d24
Revises: 1c491228ed20
Create Date: 2020-07-23 01:43:02.628934

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eb611eac7d24'
down_revision = '1c491228ed20'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('profiles', 'total_swaps')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('profiles', sa.Column('total_swaps', sa.INTEGER(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###