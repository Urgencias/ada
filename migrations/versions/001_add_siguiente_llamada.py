"""add siguiente llamada

Revision ID: 001
Revises: 
Create Date: 2024-12-22 16:47:04.502

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Añadir columna siguiente_llamada a la tabla recordatorios
    op.add_column('recordatorios', sa.Column('siguiente_llamada', sa.DateTime(), nullable=True))

    # Actualizar la tabla registro_llamadas para simplificarla
    with op.batch_alter_table('registro_llamadas') as batch_op:
        # Eliminar columnas que ya no se usan
        batch_op.drop_column('notas')
        batch_op.drop_column('respuesta')
        batch_op.drop_column('intentos')
        batch_op.drop_column('siguiente_intento')

def downgrade():
    # Eliminar columna siguiente_llamada de la tabla recordatorios
    op.drop_column('recordatorios', 'siguiente_llamada')

    # Restaurar columnas eliminadas en registro_llamadas
    with op.batch_alter_table('registro_llamadas') as batch_op:
        batch_op.add_column(sa.Column('notas', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('respuesta', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('intentos', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('siguiente_intento', sa.DateTime(), nullable=True))
