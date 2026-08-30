from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user

from app import db
from app.models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('chat.chat_index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not email or not password or len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('auth/register.html')

        if confirm_password and password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register.html')
            
        user = User.query.filter_by(email=email).first()
        if user:
            flash('An account with this email already exists.', 'error')
            return render_template('auth/register.html')
            
        new_user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        flash('Welcome to Roast & Co.!', 'success')
        return redirect(url_for('chat.chat_index'))

    return render_template('auth/register.html')

# Alias for backwards compatibility
register_get = register
register_post = register

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat.chat_index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid email or password. Please check your credentials.', 'error')
            return render_template('auth/login.html')
            
        login_user(user)
        return redirect(url_for('chat.chat_index'))

    return render_template('auth/login.html')

# Alias for backwards compatibility
login_get = login
login_post = login

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been signed out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat.chat_index'))
    return redirect(url_for('auth.login'))
