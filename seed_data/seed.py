import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Admin, Order, Document, DocumentChunk
from werkzeug.security import generate_password_hash


def seed():
    app = create_app()
    with app.app_context():
        print("Initializing authentication accounts...")
        db.create_all()

        # --- Admin Account ---
        if not Admin.query.filter_by(email='admin@roastandco.com').first():
            admin = Admin(
                email='admin@roastandco.com',
                password_hash=generate_password_hash('admin123'),
            )
            db.session.add(admin)
            db.session.commit()
            print("  [+] Admin initialized: admin@roastandco.com / admin123")

        # --- Customer Demo Users ---
        demo_users = [
            {'email': 'maria@example.com', 'pwd': 'demo123'},
            {'email': 'james.chen@example.com', 'pwd': 'demo123'},
            {'email': 'sarah.k@example.com', 'pwd': 'demo123'},
        ]

        for du in demo_users:
            u = User.query.filter_by(email=du['email']).first()
            if not u:
                u = User(
                    email=du['email'],
                    password_hash=generate_password_hash(du['pwd']),
                )
                db.session.add(u)
                db.session.commit()
                print(f"  [+] Customer initialized: {du['email']} / {du['pwd']}")

        u_count = User.query.count()
        a_count = Admin.query.count()
        o_count = Order.query.count()
        d_count = Document.query.count()

        print(f"\nSystem ready! {u_count} users, {a_count} admin, {o_count} orders, {d_count} documents.")


if __name__ == "__main__":
    seed()
