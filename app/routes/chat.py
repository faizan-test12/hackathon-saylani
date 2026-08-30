from flask import Blueprint, render_template, request, jsonify, abort, Response, stream_with_context
from flask_login import login_required, current_user

from app import db
from app.models import User, Chat, Message
from app.services.chat_agent import stream_message, process_message

chat_bp = Blueprint('chat', __name__)


def _require_customer():
    if not isinstance(current_user._get_current_object(), User):
        abort(403)


@chat_bp.route('/chat')
@login_required
def chat_index():
    _require_customer()
    chats = Chat.query.filter_by(user_id=current_user.id).order_by(Chat.updated_at.desc()).all()
    return render_template('chat/index.html', chats=chats)


@chat_bp.route('/chat/new', methods=['POST'])
@login_required
def new_chat():
    _require_customer()
    chat = Chat(user_id=current_user.id, title="New Conversation")
    db.session.add(chat)
    db.session.commit()
    return jsonify({"id": chat.id, "title": chat.title})


@chat_bp.route('/chat/<int:chat_id>/messages', methods=['GET'])
@login_required
def get_messages(chat_id):
    _require_customer()
    chat = Chat.query.get_or_404(chat_id)
    if chat.user_id != current_user.id:
        abort(403)

    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at).all()
    messages_data = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in messages
    ]
    return jsonify(messages_data)


@chat_bp.route('/chat/<int:chat_id>/message', methods=['POST'])
@login_required
def post_message(chat_id):
    _require_customer()
    chat = Chat.query.get_or_404(chat_id)
    if chat.user_id != current_user.id:
        abort(403)

    data = request.get_json() or {}
    message_text = data.get('message', '').strip()
    if not message_text:
        return jsonify({"error": "Empty message"}), 400

    # Stream response tokens via Server-Sent Events (SSE)
    return Response(
        stream_with_context(stream_message(current_user.id, chat_id, message_text)),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@chat_bp.route('/chat/<int:chat_id>', methods=['DELETE'])
@login_required
def delete_chat(chat_id):
    _require_customer()
    chat = Chat.query.get_or_404(chat_id)
    if chat.user_id != current_user.id:
        abort(403)

    db.session.delete(chat)
    db.session.commit()
    return jsonify({"ok": True})
