# Contenido del archivo migrations/twilio_migration.py
"""Migración para cambiar columnas de Netelip a Twilio"""
from flask import current_app
from flask_migrate import Migrate
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Renombrar columnas en la tabla registro_llamadas
    op.alter_column('registro_llamadas', 'id_llamada_netelip', 
                    new_column_name='id_llamada_twilio',
                    existing_type=sa.String(100))
    
    op.alter_column('registro_llamadas', 'respuesta_netelip', 
                    new_column_name='respuesta_twilio',
                    existing_type=sa.Text)

def downgrade():
    # Revertir los cambios si es necesario
    op.alter_column('registro_llamadas', 'id_llamada_twilio',
                    new_column_name='id_llamada_netelip',
                    existing_type=sa.String(100))
    
    op.alter_column('registro_llamadas', 'respuesta_twilio',
                    new_column_name='respuesta_netelip',
                    existing_type=sa.Text)
