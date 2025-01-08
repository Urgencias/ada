"""add user verification

Revision ID: 004
Revises: 003
Create Date: 2024-12-22 17:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None

def upgrade():
    # Añadir nuevos campos para verificación de email
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('email_verificado', sa.Boolean(), default=False))
        batch_op.add_column(sa.Column('fecha_registro', sa.DateTime(), server_default=sa.text('now()')))
        batch_op.add_column(sa.Column('es_admin', sa.Boolean(), default=False))
        batch_op.add_column(sa.Column('verification_token', sa.String(100), unique=True))
        batch_op.add_column(sa.Column('verification_token_expiry', sa.DateTime()))

def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('email_verificado')
        batch_op.drop_column('fecha_registro')
        batch_op.drop_column('es_admin')
        batch_op.drop_column('verification_token')
        batch_op.drop_column('verification_token_expiry')
