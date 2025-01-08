"""add subscription system

Revision ID: 009
Revises: 008
Create Date: 2024-12-26 05:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None

def upgrade():
    # Añadir campos a users para distinguir tipo de usuario y verificación
    op.add_column('users', sa.Column('tipo_usuario', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('edad', sa.Integer, nullable=True))
    op.add_column('users', sa.Column('condicion_especial', sa.String(200), nullable=True))
    op.add_column('users', sa.Column('verificacion_edad', sa.Boolean, server_default='false'))
    op.add_column('users', sa.Column('verificacion_condicion', sa.Boolean, server_default='false'))

    # Modificar paquetes_llamadas para soportar tipos de planes
    op.add_column('paquetes_llamadas', sa.Column('tipo_plan', sa.String(20), nullable=False, server_default='pago'))
    op.add_column('paquetes_llamadas', sa.Column('descripcion', sa.Text, nullable=True))
    op.add_column('paquetes_llamadas', sa.Column('limite_recordatorios', sa.Integer, nullable=False, server_default='100'))
    op.add_column('paquetes_llamadas', sa.Column('cupo_maximo', sa.Integer, nullable=True))

    # Crear tabla de suscripciones
    op.create_table(
        'suscripciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('paquete_id', sa.Integer(), nullable=False),
        sa.Column('fecha_inicio', sa.DateTime(), nullable=False),
        sa.Column('fecha_fin', sa.DateTime(), nullable=True),
        sa.Column('estado', sa.String(20), nullable=False, server_default='pendiente'),
        sa.Column('benefactor_id', sa.Integer(), nullable=True),
        sa.Column('documentacion_verificada', sa.Boolean, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['paquete_id'], ['paquetes_llamadas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['benefactor_id'], ['users.id'], ondelete='SET NULL')
    )

    # Crear índices para mejorar el rendimiento
    op.create_index('idx_suscripciones_user', 'suscripciones', ['user_id'])
    op.create_index('idx_suscripciones_benefactor', 'suscripciones', ['benefactor_id'])
    op.create_index('idx_suscripciones_estado', 'suscripciones', ['estado'])

def downgrade():
    # Eliminar índices
    op.drop_index('idx_suscripciones_estado')
    op.drop_index('idx_suscripciones_benefactor')
    op.drop_index('idx_suscripciones_user')

    # Eliminar tabla
    op.drop_table('suscripciones')

    # Eliminar columnas de paquetes_llamadas
    op.drop_column('paquetes_llamadas', 'cupo_maximo')
    op.drop_column('paquetes_llamadas', 'limite_recordatorios')
    op.drop_column('paquetes_llamadas', 'descripcion')
    op.drop_column('paquetes_llamadas', 'tipo_plan')

    # Eliminar columnas de users
    op.drop_column('users', 'verificacion_condicion')
    op.drop_column('users', 'verificacion_edad')
    op.drop_column('users', 'condicion_especial')
    op.drop_column('users', 'edad')
    op.drop_column('users', 'tipo_usuario')