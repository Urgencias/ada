"""remove audio_url

Revision ID: 002
Revises: 001
Create Date: 2024-12-22 17:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade():
    # Eliminar la columna audio_url ya que ahora usamos TTS de Netelip
    with op.batch_alter_table('recordatorios') as batch_op:
        batch_op.drop_column('audio_url')

def downgrade():
    # Restaurar la columna audio_url si necesitamos revertir
    with op.batch_alter_table('recordatorios') as batch_op:
        batch_op.add_column(sa.Column('audio_url', sa.String(255)))
