"""empty message

Revision ID: 1c491228ed20
Revises: 6c05aa8b1463
Create Date: 2020-07-23 01:31:49.981315

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1c491228ed20'
down_revision = '6c05aa8b1463'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('swaps', sa.Column('result_winnings', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('swaps', 'result_winnings')
    # ### end Alembic commands ###
