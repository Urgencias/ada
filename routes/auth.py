from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse
from models import User
from extensions import db, login_manager
from utils.formulario_recordatorios import LoginForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/logout')
@login_required
def logout():
    """Cierra la sesión del usuario actual"""
    logout_user()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('main.dashboard')
            return redirect(next_page)

        flash('Usuario o contraseña incorrectos', 'danger')

    form = LoginForm()
    return render_template('login.html', form=form)

@auth_bp.route('/recuperar-password', methods=['GET', 'POST'])
def recuperar_password():
    """Página de recuperación de contraseña"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.generate_reset_token()
            # Aquí deberías enviar el email con el token
            flash('Se ha enviado un enlace de recuperación a tu correo', 'info')
            return redirect(url_for('auth.login'))
        flash('Email no encontrado', 'danger')

    return render_template('recuperar_password.html')