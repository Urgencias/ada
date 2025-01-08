"""add payment packages

Revision ID: 005
Revises: 004
Create Date: 2024-12-22 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

def upgrade():
    # Crear tabla de paquetes de llamadas
    op.create_table(
        'paquetes_llamadas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(100), nullable=False),
        sa.Column('cantidad_llamadas', sa.Integer(), nullable=False),
        sa.Column('precio', sa.Numeric(10, 2), nullable=False),
        sa.Column('activo', sa.Boolean(), default=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Crear tabla de códigos promocionales
    op.create_table(
        'codigos_promocionales',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(50), unique=True, nullable=False),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('descuento', sa.Integer(), nullable=False),
        sa.Column('user_referidor_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('fecha_creacion', sa.DateTime(), default=datetime.utcnow),
        sa.Column('fecha_expiracion', sa.DateTime()),
        sa.Column('usos_maximos', sa.Integer()),
        sa.Column('usos_actuales', sa.Integer(), default=0),
        sa.Column('activo', sa.Boolean(), default=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Añadir campos a la tabla users
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('llamadas_disponibles', sa.Integer(), default=0))
        batch_op.add_column(sa.Column('es_referido_de_id', sa.Integer(), sa.ForeignKey('users.id')))

    # Insertar paquetes predefinidos
    op.execute("""
        INSERT INTO paquetes_llamadas (nombre, cantidad_llamadas, precio, activo)
        VALUES 
        ('Básico', 100, 29.99, true),
        ('Estándar', 150, 39.99, true),
        ('Plus', 200, 49.99, true),
        ('Premium', 250, 59.99, true),
        ('Pro', 300, 69.99, true),
        ('Empresarial', 500, 99.99, true)
    """)

def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('llamadas_disponibles')
        batch_op.drop_column('es_referido_de_id')

    op.drop_table('codigos_promocionales')
    op.drop_table('paquetes_llamadas')
