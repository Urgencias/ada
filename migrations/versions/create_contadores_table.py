"""create contadores table

Revision ID: create_contadores_table
Revises: 
Create Date: 2024-12-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_contadores_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'contadores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('mensajes_totales', sa.Integer(), default=0),
        sa.Column('mensajes_mes_actual', sa.Integer(), default=0),
        sa.Column('abuelos_adoptados', sa.Integer(), default=0),
        sa.Column('tipo_suscripcion', sa.String(50), nullable=False),
        sa.Column('limite_mensajes', sa.Integer(), default=100),
        sa.Column('fecha_actualizacion', sa.DateTime(), nullable=False),
        sa.Column('llamadas_totales', sa.Integer(), default=0),
        sa.Column('llamadas_completadas', sa.Integer(), default=0),
        sa.Column('llamadas_pendientes', sa.Integer(), default=0),
        sa.Column('llamadas_en_curso', sa.Integer(), default=0),
        sa.Column('llamadas_error', sa.Integer(), default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['usuario_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('usuario_id')
    )

def downgrade():
    op.drop_table('contadores')
