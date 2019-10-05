"""empty message

Revision ID: 29661fa98129
Revises: d03a9ae2d343
Create Date: 2019-10-05 14:45:06.928248

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '29661fa98129'
down_revision = 'd03a9ae2d343'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('flights', sa.Column('day', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('flights', 'day')
    # ### end Alembic commands ###