"""add missing user columns

Revision ID: 006
Revises: 005
Create Date: 2024-12-22 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

def upgrade():
    # Añadir columnas faltantes a la tabla users
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('llamadas_realizadas', sa.Integer(), default=0))
        batch_op.add_column(sa.Column('pago_verificado', sa.Boolean(), default=False))

        # Verificar si las columnas existen antes de crearlas
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        columns = [col['name'] for col in inspector.get_columns('users')]

        if 'email_verificado' not in columns:
            batch_op.add_column(sa.Column('email_verificado', sa.Boolean(), default=False))
        if 'verification_token' not in columns:
            batch_op.add_column(sa.Column('verification_token', sa.String(100), unique=True))
        if 'verification_token_expiry' not in columns:
            batch_op.add_column(sa.Column('verification_token_expiry', sa.DateTime()))

def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('llamadas_realizadas')
        batch_op.drop_column('pago_verificado')
