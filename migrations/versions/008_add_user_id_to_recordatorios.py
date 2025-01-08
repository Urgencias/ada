"""add user_id to recordatorios

Revision ID: 008
Revises: 007
Create Date: 2024-12-22 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None

def upgrade():
    # Añadir columna user_id a la tabla recordatorios
    with op.batch_alter_table('recordatorios') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_recordatorio_user',
            'users',
            ['user_id'],
            ['id']
        )
    
    # Asignar un usuario por defecto (admin) a los recordatorios existentes
    op.execute("""
        UPDATE recordatorios
        SET user_id = (SELECT id FROM users WHERE username = 'admin')
        WHERE user_id IS NULL
    """)
    
    # Hacer la columna no nullable después de la migración de datos
    with op.batch_alter_table('recordatorios') as batch_op:
        batch_op.alter_column('user_id', nullable=False)

def downgrade():
    with op.batch_alter_table('recordatorios') as batch_op:
        batch_op.drop_constraint('fk_recordatorio_user', type_='foreignkey')
        batch_op.drop_column('user_id')
