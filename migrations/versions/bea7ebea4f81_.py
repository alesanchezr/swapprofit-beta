"""empty message

Revision ID: bea7ebea4f81
Revises: cd23bf7fe08e
Create Date: 2019-12-27 00:39:37.151073

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bea7ebea4f81'
down_revision = 'cd23bf7fe08e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('devices_user_id_fkey', 'devices', type_='foreignkey')
    op.create_foreign_key(None, 'devices', 'profiles', ['user_id'], ['id'])
    op.drop_constraint('transactions_user_id_fkey', 'transactions', type_='foreignkey')
    op.create_foreign_key(None, 'transactions', 'profiles', ['user_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'transactions', type_='foreignkey')
    op.create_foreign_key('transactions_user_id_fkey', 'transactions', 'users', ['user_id'], ['id'])
    op.drop_constraint(None, 'devices', type_='foreignkey')
    op.create_foreign_key('devices_user_id_fkey', 'devices', 'users', ['user_id'], ['id'])
    # ### end Alembic commands ###
