"""Add provider column to registro_llamadas

Revision ID: add_provider_column
Revises: 
Create Date: 2024-12-25 12:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_provider_column'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('registro_llamadas', sa.Column('proveedor', sa.String(50), nullable=True))
    # Establecer valor por defecto para registros existentes
    op.execute("UPDATE registro_llamadas SET proveedor = 'netelip' WHERE proveedor IS NULL")

def downgrade():
    op.drop_column('registro_llamadas', 'proveedor')
