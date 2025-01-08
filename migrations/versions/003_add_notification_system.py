"""add notification system

Revision ID: 003
Revises: 002
Create Date: 2024-12-22 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade():
    # Crear tabla de números autorizados
    op.create_table(
        'numeros_autorizados',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('numero', sa.String(20), nullable=False),
        sa.Column('descripcion', sa.String(100)),
        sa.Column('activo', sa.Boolean(), default=True),
        sa.Column('fecha_registro', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.UniqueConstraint('user_id', 'numero', name='uq_usuario_numero')
    )

    # Crear tabla de notificaciones
    op.create_table(
        'notificaciones_llamadas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recordatorio_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(50), nullable=False),  # 'iniciada', 'en_curso', 'finalizada', 'error'
        sa.Column('mensaje', sa.Text(), nullable=False),
        sa.Column('fecha_creacion', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('leida', sa.Boolean(), default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['recordatorio_id'], ['recordatorios.id'], )
    )

    # Añadir contador de llamadas a la tabla de usuarios
    op.add_column('users', sa.Column('llamadas_realizadas', sa.Integer(), server_default='0'))

def downgrade():
    op.drop_table('notificaciones_llamadas')
    op.drop_table('numeros_autorizados')
    op.drop_column('users', 'llamadas_realizadas')
