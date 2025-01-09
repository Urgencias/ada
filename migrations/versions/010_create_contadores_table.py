"""create contadores table

Revision ID: 010
Revises: 009
Create Date: 2024-12-28 23:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'contadores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('llamadas_totales', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('llamadas_completadas', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('llamadas_pendientes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('llamadas_en_curso', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('llamadas_error', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ultima_actualizacion', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['usuario_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('usuario_id')
    )

    # Crear índices para mejorar el rendimiento
    op.create_index('idx_contadores_usuario', 'contadores', ['usuario_id'])
    op.create_index('idx_contadores_ultima_actualizacion', 'contadores', ['ultima_actualizacion'])

def downgrade():
    # Eliminar índices
    op.drop_index('idx_contadores_ultima_actualizacion')
    op.drop_index('idx_contadores_usuario')

    # Eliminar tabla
    op.drop_table('contadores')
