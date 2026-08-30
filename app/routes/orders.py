from flask import Blueprint, jsonify, abort, request, render_template
from flask_login import login_required, current_user

from app.models import User, Order

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/orders', methods=['GET'])
@login_required
def get_orders():
    if not isinstance(current_user._get_current_object(), User):
        abort(403)
        
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    
    if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
        orders_data = [
            {
                "id": o.id,
                "items": o.items,
                "address": o.address,
                "status": o.status,
                "created_at": o.created_at.isoformat() if hasattr(o, 'created_at') and o.created_at else None
            }
            for o in orders
        ]
        return jsonify(orders_data)
        
    return render_template('orders/index.html', orders=orders)

# Alias for backwards compatibility
list_orders = get_orders
