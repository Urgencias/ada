"""extend notificaciones table

Revision ID: 007
Revises: 006
Create Date: 2024-12-22 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None

def upgrade():
    # Añadir nuevas columnas a la tabla notificaciones_llamadas
    with op.batch_alter_table('notificaciones_llamadas') as batch_op:
        batch_op.add_column(sa.Column('nivel', sa.String(20), server_default='info'))
        batch_op.add_column(sa.Column('datos_extra', sa.JSON))

def downgrade():
    with op.batch_alter_table('notificaciones_llamadas') as batch_op:
        batch_op.drop_column('nivel')
        batch_op.drop_column('datos_extra')
