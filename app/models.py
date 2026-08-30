import json
from datetime import datetime, timezone
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    chats = db.relationship("Chat", backref="user", lazy="dynamic")
    orders = db.relationship("Order", backref="user", lazy="dynamic")

    def get_id(self):
        """Prefix so the shared user_loader can tell User from Admin."""
        return f"u_{self.id}"


class Admin(UserMixin, db.Model):
    __tablename__ = "admin"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def get_id(self):
        return f"a_{self.id}"


class Chat(db.Model):
    __tablename__ = "chat"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), default="New chat")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages = db.relationship(
        "Message", backref="chat", order_by="Message.created_at", lazy="dynamic"
    )


class Message(db.Model):
    __tablename__ = "message"

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user | assistant | tool
    content = db.Column(db.Text, nullable=False)
    tool_calls = db.Column(db.JSON, nullable=True)
    prompt_tokens = db.Column(db.Integer, default=0)
    completion_tokens = db.Column(db.Integer, default=0)
    cost_usd = db.Column(db.Numeric(10, 6), default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Order(db.Model):
    __tablename__ = "order"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    items = db.Column(db.JSON, nullable=False)  # [{sku, name, qty, price}]
    address = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default="placed")  # placed|shipped|delivered|cancelled
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Document(db.Model):
    __tablename__ = "document"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # cascade delete-orphan so removing a doc truly removes chunks from retrieval
    chunks = db.relationship(
        "DocumentChunk", backref="document", cascade="all, delete-orphan"
    )


class DocumentChunk(db.Model):
    """Each row is a text chunk + its embedding vector (stored as JSON for SQLite compat)."""
    __tablename__ = "document_chunk"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("document.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    # 384-dim float vector serialised as JSON text — cosine search done in Python
    embedding_json = db.Column(db.Text, nullable=False, default="[]")

    # --------------- helpers ---------------
    def set_embedding(self, vec: list[float]):
        self.embedding_json = json.dumps(vec)

    def get_embedding(self) -> list[float]:
        return json.loads(self.embedding_json)
