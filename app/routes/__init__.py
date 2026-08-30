"""
Routes Package
==============
Exports the core blueprints for authentication, chat, order management, and administrative audit.
"""

from app.routes.auth import auth_bp
from app.routes.chat import chat_bp
from app.routes.orders import orders_bp
from app.routes.admin import admin_bp

__all__ = ["auth_bp", "chat_bp", "orders_bp", "admin_bp"]
