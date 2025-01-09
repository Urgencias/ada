"""Migración para renombrar columnas de Twilio a nombres genéricos"""
from flask import current_app
from flask_migrate import Migrate
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Renombrar columnas en la tabla registro_llamadas
    with op.batch_alter_table('registro_llamadas') as batch_op:
        # Renombrar id_llamada_twilio a id_llamada
        batch_op.alter_column('id_llamada_twilio', 
                            new_column_name='id_llamada',
                            existing_type=sa.String(100))

        # Renombrar respuesta_twilio a respuesta
        batch_op.alter_column('respuesta_twilio', 
                            new_column_name='respuesta',
                            existing_type=sa.Text)

def downgrade():
    # Revertir los cambios si es necesario
    with op.batch_alter_table('registro_llamadas') as batch_op:
        # Revertir id_llamada a id_llamada_twilio
        batch_op.alter_column('id_llamada',
                            new_column_name='id_llamada_twilio',
                            existing_type=sa.String(100))

        # Revertir respuesta a respuesta_twilio
        batch_op.alter_column('respuesta',
                            new_column_name='respuesta_twilio',
                            existing_type=sa.Text)
