"""
Roast & Co. — Application Factory & Extension Initialization
============================================================
Initializes Flask, SQLAlchemy, Flask-Migrate, Flask-Login, and registers
modular blueprints (auth, chat, admin, orders).
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Core Flask Extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app() -> Flask:
    """
    Flask Application Factory.
    Configures database connections, login loaders, and blueprint routes.
    """
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # Ensure required instance and document upload directories exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config.get("UPLOAD_FOLDER", ""), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # ---- Dual-Scope User Loader (User vs Admin) ----
    from app.models import User, Admin

    @login_manager.user_loader
    def load_user(compound_id: str):
        """
        Loads the active session user based on the prefix:
          - 'u_<id>' -> Customer User
          - 'a_<id>' -> Store Admin
        """
        try:
            kind, raw_id = compound_id.split("_", 1)
            uid = int(raw_id)
        except (ValueError, AttributeError):
            return None

        if kind == "u":
            return db.session.get(User, uid)
        if kind == "a":
            return db.session.get(Admin, uid)
        return None

    # ---- Blueprint Registrations ----
    from app.routes.auth import auth_bp
    from app.routes.chat import chat_bp
    from app.routes.admin import admin_bp
    from app.routes.orders import orders_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(orders_bp)

    return app
