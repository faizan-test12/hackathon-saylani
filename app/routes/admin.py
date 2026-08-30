import os
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func

from app import db
from app.models import Admin, User, Chat, Message, Document
from app.services.rag import ingest_document

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not isinstance(current_user._get_current_object(), Admin):
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated


# ── Auth ──

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and isinstance(current_user._get_current_object(), Admin):
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        admin = Admin.query.filter_by(email=email).first()
        if not admin or not check_password_hash(admin.password_hash, password):
            flash('Invalid admin credentials.', 'error')
            return render_template('admin/login.html')

        login_user(admin)
        flash('Admin session authenticated.', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/login.html')


@admin_bp.route('/logout')
def admin_logout():
    logout_user()
    flash('Admin session signed out.', 'info')
    return redirect(url_for('admin.admin_login'))


# ── Dashboard ──

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_messages = db.session.query(func.count(Message.id)).scalar() or 0
    total_tokens = db.session.query(
        func.coalesce(func.sum(Message.prompt_tokens + Message.completion_tokens), 0)
    ).scalar() or 0
    total_cost = float(db.session.query(
        func.coalesce(func.sum(Message.cost_usd), 0)
    ).scalar() or 0)

    # per-user stats — return dicts so Jinja2 + tojson work cleanly
    rows = db.session.query(
        User.id,
        User.email,
        func.count(Message.id).label('message_count'),
        func.coalesce(func.sum(Message.prompt_tokens + Message.completion_tokens), 0).label('total_tokens'),
        func.coalesce(func.sum(Message.cost_usd), 0).label('total_cost'),
    ).outerjoin(Chat, User.id == Chat.user_id) \
     .outerjoin(Message, Chat.id == Message.chat_id) \
     .group_by(User.id, User.email).all()

    per_user_stats = [
        {
            'user_id': r.id,
            'email': r.email,
            'message_count': r.message_count,
            'total_tokens': int(r.total_tokens),
            'total_cost': float(r.total_cost),
        }
        for r in rows
    ]

    # per-chat stats
    chat_rows = db.session.query(
        Chat.id,
        Chat.title,
        User.email,
        func.count(Message.id).label('message_count'),
        func.coalesce(func.sum(Message.prompt_tokens + Message.completion_tokens), 0).label('total_tokens'),
        func.coalesce(func.sum(Message.cost_usd), 0).label('total_cost'),
    ).join(User, User.id == Chat.user_id) \
     .outerjoin(Message, Chat.id == Message.chat_id) \
     .group_by(Chat.id, Chat.title, User.email).all()

    per_chat_stats = [
        {
            'chat_id': r.id,
            'chat_title': r.title or 'Untitled',
            'user_email': r.email,
            'message_count': r.message_count,
            'total_tokens': int(r.total_tokens),
            'total_cost': float(r.total_cost),
        }
        for r in chat_rows
    ]

    return render_template(
        'admin/dashboard.html',
        total_messages=total_messages,
        total_tokens=total_tokens,
        total_cost=total_cost,
        per_user_stats=per_user_stats,
        per_chat_stats=per_chat_stats,
    )


# ── Documents ──

@admin_bp.route('/documents')
@admin_required
def documents():
    docs = Document.query.order_by(Document.uploaded_at.desc()).all()
    return render_template('admin/documents.html', documents=docs)


@admin_bp.route('/documents/upload', methods=['POST'])
@admin_required
def upload_document():
    if 'file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('admin.documents'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('admin.documents'))

    allowed = file.filename.lower().endswith(('.pdf', '.txt', '.md'))
    if not allowed:
        flash('Only .pdf, .txt, and .md files are accepted.', 'error')
        return redirect(url_for('admin.documents'))

    filename = secure_filename(file.filename)
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)

    try:
        ingest_document(file_path, filename)
        flash(f'"{filename}" uploaded and indexed successfully.', 'success')
    except Exception as e:
        flash(f'Upload failed: {e}', 'error')

    return redirect(url_for('admin.documents'))


@admin_bp.route('/documents/<int:doc_id>/delete', methods=['POST'])
@admin_required
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    db.session.delete(doc)  # cascade deletes chunks + embeddings
    db.session.commit()
    flash('Document deleted and vector index purged.', 'success')
    return redirect(url_for('admin.documents'))


# ── View-as (browse any user's chats) ──

@admin_bp.route('/users')
@admin_required
def users():
    users_list = db.session.query(
        User,
        func.count(Chat.id).label('chat_count'),
    ).outerjoin(Chat).group_by(User.id).all()
    return render_template('admin/users.html', users=users_list)

# Alias for backwards compatibility
users_list = users


@admin_bp.route('/users/<int:user_id>/chats')
@admin_required
def user_chats(user_id):
    target_user = User.query.get_or_404(user_id)
    chats = Chat.query.filter_by(user_id=user_id).order_by(Chat.updated_at.desc()).all()
    return render_template('admin/user_chats.html', target_user=target_user, chats=chats)


@admin_bp.route('/chats/<int:chat_id>')
@admin_required
def chat_view(chat_id):
    chat = Chat.query.get_or_404(chat_id)
    user = User.query.get(chat.user_id)
    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at).all()
    return render_template(
        'admin/chat_view.html',
        chat=chat,
        messages=messages,
        user_email=user.email if user else 'Unknown',
    )
