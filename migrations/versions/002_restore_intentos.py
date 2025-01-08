"""restore intentos columns

Revision ID: 002
Revises: 001
Create Date: 2024-12-22 16:50:00.000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade():
    # Restaurar columnas necesarias en registro_llamadas
    with op.batch_alter_table('registro_llamadas') as batch_op:
        batch_op.add_column(sa.Column('intentos', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('siguiente_intento', sa.DateTime(), nullable=True))

def downgrade():
    # Eliminar columnas restauradas
    with op.batch_alter_table('registro_llamadas') as batch_op:
        batch_op.drop_column('siguiente_intento')
        batch_op.drop_column('intentos')
