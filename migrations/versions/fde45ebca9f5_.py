"""empty message

Revision ID: fde45ebca9f5
Revises: 0fb0333f7516
Create Date: 2020-07-22 20:43:55.762792

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fde45ebca9f5'
down_revision = '0fb0333f7516'
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
