import logging
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DateField, TimeField
from wtforms.validators import DataRequired, Length, ValidationError
from datetime import datetime
from flask import session
import re

logger = logging.getLogger(__name__)

class FormularioRecordatorio(FlaskForm):
    """Formulario para crear y editar recordatorios"""

    nombre = StringField('Nombre', 
                        validators=[DataRequired(message="El nombre es requerido"), 
                                        Length(min=2, max=100, message="El nombre debe tener entre 2 y 100 caracteres")])

    telefono = StringField('Teléfono', 
                       validators=[DataRequired(message="El teléfono es requerido")],
                       render_kw={
                           "value": "0034",
                           "class": "form-control form-control-lg"
                       })

    fecha = DateField('Fecha', 
                     validators=[DataRequired(message="La fecha es requerida")],
                     render_kw={
                         "class": "form-control form-control-lg datepicker",
                         "data-provide": "datepicker",
                         "data-date-format": "yyyy-mm-dd"
                     })

    hora = TimeField('Hora', 
                    validators=[DataRequired(message="La hora es requerida")],
                    render_kw={
                        "class": "form-control form-control-lg timepicker",
                        "data-provide": "timepicker",
                        "data-show-meridian": "false"
                    })

    tipo = SelectField('Tipo',
                      choices=[
                          ('personal', 'Recordatorio Personal'),
                          ('trabajo', 'Reunión de Trabajo'),
                          ('evento', 'Evento Importante'),
                          ('otros', 'Otros Recordatorios')
                      ],
                      validators=[DataRequired(message="El tipo es requerido")],
                      render_kw={"class": "form-select form-select-lg"})

    repeticion = SelectField('Frecuencia de repetición',
                           choices=[
                               ('0', 'Sin repetición (una sola vez)'),
                               ('24', 'Una vez al día (cada 24 horas)'),
                               ('12', 'Dos veces al día (cada 12 horas)'),
                               ('8', 'Tres veces al día (cada 8 horas)'),
                               ('6', 'Cuatro veces al día (cada 6 horas)'),
                               ('4', 'Seis veces al día (cada 4 horas)'),
                               ('2', 'Doce veces al día (cada 2 horas)'),
                               ('1', 'Cada hora')
                           ],
                           default='0',
                           validators=[DataRequired(message="La frecuencia es requerida")],
                           render_kw={"class": "form-select form-select-lg"})

    mensaje = TextAreaField('Mensaje del recordatorio',
                          validators=[
                              DataRequired(message="El mensaje es requerido"), 
                              Length(min=10, max=500, 
                                    message="El mensaje debe tener entre 10 y 500 caracteres")
                          ],
                          render_kw={
                              "placeholder": "Sea claro y específico. Este mensaje se convertirá en voz.",
                              "class": "form-control form-control-lg",
                              "rows": "4"
                          })

    def validate_telefono(self, field):
        """Valida el formato del número de teléfono"""
        try:
            # Obtener el número y asegurarse que empiece con 0034
            telefono = field.data.strip()
            if not telefono.startswith('0034'):
                telefono = '0034' + telefono.lstrip('0').lstrip('34')

            # Verificar que tenga los 9 dígitos después del 0034
            numero_sin_prefijo = telefono[4:]
            if not numero_sin_prefijo.isdigit() or len(numero_sin_prefijo) != 9:
                raise ValidationError('Por favor, introduzca 9 dígitos después del 0034')

            # Guardar el número normalizado
            field.data = telefono
            logger.debug(f"Número validado y normalizado: {telefono}")

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error en validación de teléfono: {str(e)}")
            raise ValidationError('Por favor, introduzca 9 dígitos después del 0034')

    def __init__(self, *args, **kwargs):
        """Inicializar el formulario con valores previos de la sesión"""
        super(FormularioRecordatorio, self).__init__(*args, **kwargs)
        if not self.is_submitted():
            # Cargar valores previos de la sesión si existen
            if 'ultimo_recordatorio' in session:
                ultimo = session.get('ultimo_recordatorio', {})
                self.nombre.data = ultimo.get('nombre', self.nombre.data)
                self.telefono.data = ultimo.get('telefono', self.telefono.data)
                self.tipo.data = ultimo.get('tipo', self.tipo.data)
                self.repeticion.data = ultimo.get('repeticion', self.repeticion.data)


from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])