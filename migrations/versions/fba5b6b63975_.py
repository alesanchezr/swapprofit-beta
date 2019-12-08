"""empty message

Revision ID: fba5b6b63975
Revises: 0d045a7df76f
Create Date: 2019-12-08 18:43:08.137205

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fba5b6b63975'
down_revision = '0d045a7df76f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('buy_ins', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('buy_ins', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('coins', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('coins', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('devices', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('devices', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('flights', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('flights', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('profiles', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('profiles', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('swaps', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('swaps', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('tournaments', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('tournaments', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('transactions', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('transactions', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('zip_codes', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('zip_codes', sa.Column('updated_at', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('zip_codes', 'updated_at')
    op.drop_column('zip_codes', 'created_at')
    op.drop_column('transactions', 'updated_at')
    op.drop_column('transactions', 'created_at')
    op.drop_column('tournaments', 'updated_at')
    op.drop_column('tournaments', 'created_at')
    op.drop_column('swaps', 'updated_at')
    op.drop_column('swaps', 'created_at')
    op.drop_column('profiles', 'updated_at')
    op.drop_column('profiles', 'created_at')
    op.drop_column('flights', 'updated_at')
    op.drop_column('flights', 'created_at')
    op.drop_column('devices', 'updated_at')
    op.drop_column('devices', 'created_at')
    op.drop_column('coins', 'updated_at')
    op.drop_column('coins', 'created_at')
    op.drop_column('buy_ins', 'updated_at')
    op.drop_column('buy_ins', 'created_at')
    # ### end Alembic commands ###
