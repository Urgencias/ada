"""update subscription model

Revision ID: 010
Revises: 009
Create Date: 2024-12-26 06:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None

def upgrade():
    # Añadir campos de tipo de usuario a la tabla users
    op.add_column('users', sa.Column('tipo_usuario', sa.String(20)))

    # Modificar tabla de suscripciones
    with op.batch_alter_table('suscripciones') as batch_op:
        # Primero eliminar la columna user_id si existe
        batch_op.drop_column('user_id', type_='foreignkey')

        # Añadir las nuevas columnas
        batch_op.add_column(sa.Column('beneficiary_id', sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('benefactor_id', sa.Integer(), nullable=True))

        # Crear foreign keys
        batch_op.create_foreign_key(
            'fk_suscripcion_beneficiary', 'users',
            ['beneficiary_id'], ['id'], ondelete='CASCADE'
        )
        batch_op.create_foreign_key(
            'fk_suscripcion_benefactor', 'users',
            ['benefactor_id'], ['id'], ondelete='SET NULL'
        )

def downgrade():
    with op.batch_alter_table('suscripciones') as batch_op:
        batch_op.drop_constraint('fk_suscripcion_benefactor', type_='foreignkey')
        batch_op.drop_constraint('fk_suscripcion_beneficiary', type_='foreignkey')
        batch_op.drop_column('benefactor_id')
        batch_op.drop_column('beneficiary_id')
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=False))

    op.drop_column('users', 'tipo_usuario')