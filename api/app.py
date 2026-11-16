"""Orbit Eats API - Flask + SQLAlchemy + MySQL.

Run:  python app.py   ->  http://127.0.0.1:8000
The tables must exist first (load orbit_eats_schema.sql into MySQL).
Every route except the GUI files requires the header:
    Authorization: Bearer <API_TOKEN>
"""
import os

from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow.sqla import SQLAlchemyAutoSchema
from marshmallow import ValidationError
from sqlalchemy.exc import DBAPIError, IntegrityError

app = Flask(__name__, static_folder='static')

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 'mysql+pymysql://root:change-me@localhost:3306/orbit_eats'
)
# NFR-01: up to 20 connections so 20 simultaneous orders do not wait for each other
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_size': 20, 'pool_pre_ping': True}

API_TOKEN = os.getenv('API_TOKEN', 'token-secreto-123')

db = SQLAlchemy(app)


# ======================================================================
# Models (one class per table in orbit_eats_schema.sql)
# ======================================================================
class Customer(db.Model):
    __tablename__ = 'customer'
    customer_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    registration_date = db.Column(db.Date, server_default=db.func.current_date())


class Employee(db.Model):
    __tablename__ = 'employee'
    employee_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(150))
    phone = db.Column(db.String(15), nullable=False)
    area = db.Column(db.String(20), nullable=False)
    hire_date = db.Column(db.Date, nullable=False)


class Product(db.Model):
    __tablename__ = 'product'
    product_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255))
    base_price = db.Column(db.Numeric(8, 2), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    available = db.Column(db.Boolean, server_default=db.true())


class Ingredient(db.Model):
    __tablename__ = 'ingredient'
    ingredient_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    unit_of_measure = db.Column(db.String(10), nullable=False)
    current_stock = db.Column(db.Numeric(10, 2), server_default='0')
    minimum_stock = db.Column(db.Numeric(10, 2), server_default='0')


class Supplier(db.Model):
    __tablename__ = 'supplier'
    supplier_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    company = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100))


class Supply(db.Model):
    __tablename__ = 'supply'
    supply_id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.supplier_id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.ingredient_id'), nullable=False)
    purchase_price = db.Column(db.Numeric(8, 2), nullable=False)
    last_purchase_date = db.Column(db.Date, nullable=False)


class ProductIngredient(db.Model):
    __tablename__ = 'product_ingredient'
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.ingredient_id'), primary_key=True)
    quantity_required = db.Column(db.Numeric(8, 2), nullable=False)


class Orders(db.Model):
    __tablename__ = 'orders'
    order_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.customer_id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.employee_id'))
    order_datetime = db.Column(db.DateTime, server_default=db.func.now())
    delivery_address = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), server_default='received')
    total = db.Column(db.Numeric(10, 2), server_default='0')
    details = db.relationship('OrderDetail', backref='order')


class OrderDetail(db.Model):
    __tablename__ = 'order_detail'
    order_detail_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(8, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)


# ======================================================================
# Schemas: validate the JSON that comes in and convert rows to JSON
# (dump_only = generated by the database, never sent by the client)
# ======================================================================
class CustomerSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Customer
        dump_only = ('customer_id', 'registration_date')


class EmployeeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Employee
        dump_only = ('employee_id',)


class ProductSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        dump_only = ('product_id',)


class IngredientSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Ingredient
        dump_only = ('ingredient_id',)


class SupplierSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Supplier
        dump_only = ('supplier_id',)


class SupplySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Supply
        include_fk = True
        dump_only = ('supply_id',)


class OrderDetailSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = OrderDetail
        include_fk = True


class OrdersSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Orders
        include_fk = True


# ======================================================================
# Security (NFR-02) and error handling
# ======================================================================
@app.before_request
def check_token():
    # The GUI files are public; every API route needs the token
    if request.endpoint in ('index', 'static'):
        return None
    if request.headers.get('Authorization') != f'Bearer {API_TOKEN}':
        return jsonify({'message': 'Unauthorized: missing or invalid token'}), 401
    return None


@app.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({'errors': error.messages}), 400


@app.errorhandler(IntegrityError)
def handle_integrity_error(error):
    # Duplicate email, foreign key to a row that does not exist, etc.
    db.session.rollback()
    return jsonify({'message': 'Integrity error', 'detail': str(error.orig)}), 409


@app.errorhandler(DBAPIError)
def handle_database_error(error):
    # CHECK constraints (invalid status, negative price...) end up here
    db.session.rollback()
    return jsonify({'message': 'Database rejected the operation', 'detail': str(error.orig)}), 400


def not_found(name):
    return jsonify({'message': f'{name} not found'}), 404


# ======================================================================
# Generic CRUD: the same 5 routes for every simple table
#   GET    /<resource>        list all
#   GET    /<resource>/<id>   get one
#   POST   /<resource>        create
#   PUT    /<resource>/<id>   update (only the fields sent)
#   DELETE /<resource>/<id>   delete
# ======================================================================
def register_crud(resource, model, schema_class, label):
    def list_all():
        return jsonify(schema_class(many=True).dump(model.query.all())), 200

    def get_one(id):
        row = db.session.get(model, id)
        if row is None:
            return not_found(label)
        return jsonify(schema_class().dump(row)), 200

    def create():
        data = schema_class().load(request.get_json() or {})
        row = model(**data)
        db.session.add(row)
        db.session.commit()
        return jsonify(schema_class().dump(row)), 201

    def update(id):
        row = db.session.get(model, id)
        if row is None:
            return not_found(label)
        data = schema_class().load(request.get_json() or {}, partial=True)
        for field, value in data.items():
            setattr(row, field, value)
        db.session.commit()
        return jsonify(schema_class().dump(row)), 200

    def delete(id):
        row = db.session.get(model, id)
        if row is None:
            return not_found(label)
        db.session.delete(row)
        db.session.commit()
        return jsonify({'message': f'{label} {id} deleted'}), 200

    app.add_url_rule(f'/{resource}', f'list_{resource}', list_all, methods=['GET'])
    app.add_url_rule(f'/{resource}/<int:id>', f'get_{resource}', get_one, methods=['GET'])
    app.add_url_rule(f'/{resource}', f'create_{resource}', create, methods=['POST'])
    app.add_url_rule(f'/{resource}/<int:id>', f'update_{resource}', update, methods=['PUT'])
    app.add_url_rule(f'/{resource}/<int:id>', f'delete_{resource}', delete, methods=['DELETE'])


register_crud('customers', Customer, CustomerSchema, 'Customer')
register_crud('employees', Employee, EmployeeSchema, 'Employee')
register_crud('products', Product, ProductSchema, 'Product')
register_crud('ingredients', Ingredient, IngredientSchema, 'Ingredient')
register_crud('suppliers', Supplier, SupplierSchema, 'Supplier')
register_crud('supplies', Supply, SupplySchema, 'Supply')


# ======================================================================
# Orders (FR-02, FR-06): an order and its lines are saved together
# ======================================================================
def order_to_json(order):
    result = OrdersSchema().dump(order)
    result['details'] = OrderDetailSchema(many=True).dump(order.details)
    return result


@app.route('/orders', methods=['GET'])
def list_orders():
    query = Orders.query
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    orders = query.order_by(Orders.order_id.desc()).all()
    return jsonify([order_to_json(o) for o in orders]), 200


@app.route('/orders/<int:id>', methods=['GET'])
def get_order(id):
    order = db.session.get(Orders, id)
    if order is None:
        return not_found('Order')
    return jsonify(order_to_json(order)), 200


@app.route('/orders', methods=['POST'])
def create_order():
    """Body: {"customer_id": 1, "delivery_address": "...",
              "items": [{"product_id": 1, "quantity": 2}, ...]}"""
    data = request.get_json() or {}
    items = data.get('items') or []
    if not data.get('customer_id') or not data.get('delivery_address') or not items:
        return jsonify({'message': 'customer_id, delivery_address and items are required'}), 400

    order = Orders(
        customer_id=data['customer_id'],
        employee_id=data.get('employee_id'),
        delivery_address=data['delivery_address'],
        status='received',
    )
    total = 0
    for item in items:
        product = db.session.get(Product, item.get('product_id'))
        if product is None or not product.available:
            return jsonify({'message': f"Product {item.get('product_id')} not available"}), 400
        quantity = int(item.get('quantity', 0))
        # FR-06: the price is copied at the moment of purchase
        subtotal = product.base_price * quantity
        order.details.append(OrderDetail(product_id=product.product_id, quantity=quantity,
                                         unit_price=product.base_price, subtotal=subtotal))
        total += subtotal
    order.total = total

    db.session.add(order)
    db.session.commit()   # one transaction: the order and all its lines, or nothing
    return jsonify(order_to_json(order)), 201


@app.route('/orders/<int:id>', methods=['PATCH'])
def update_order(id):
    """Change the status and/or assign the delivery employee.
    Body: {"status": "preparing"} or {"employee_id": 1}"""
    order = db.session.get(Orders, id)
    if order is None:
        return not_found('Order')
    data = request.get_json() or {}
    if 'status' in data:
        order.status = data['status']
    if 'employee_id' in data:
        order.employee_id = data['employee_id']
    db.session.commit()
    return jsonify(order_to_json(order)), 200


@app.route('/orders/<int:id>', methods=['DELETE'])
def cancel_order(id):
    # Orders are never erased: they are marked as cancelled to keep the sales history
    order = db.session.get(Orders, id)
    if order is None:
        return not_found('Order')
    order.status = 'cancelled'
    db.session.commit()
    return jsonify(order_to_json(order)), 200


# ======================================================================
# Recipes, stock and suppliers (FR-03, FR-04, FR-05)
# ======================================================================
@app.route('/products/<int:id>/recipe', methods=['GET'])
def get_recipe(id):
    rows = (db.session.query(Ingredient.name, Ingredient.unit_of_measure,
                             ProductIngredient.quantity_required)
            .join(ProductIngredient, ProductIngredient.ingredient_id == Ingredient.ingredient_id)
            .filter(ProductIngredient.product_id == id).all())
    return jsonify([{'ingredient': r.name, 'quantity_required': float(r.quantity_required),
                     'unit_of_measure': r.unit_of_measure} for r in rows]), 200


@app.route('/products/<int:id>/recipe', methods=['POST'])
def add_to_recipe(id):
    """Body: {"ingredient_id": 2, "quantity_required": 1}"""
    data = request.get_json() or {}
    line = ProductIngredient(product_id=id, ingredient_id=data.get('ingredient_id'),
                             quantity_required=data.get('quantity_required'))
    db.session.add(line)
    db.session.commit()
    return jsonify({'message': 'Ingredient added to recipe'}), 201


@app.route('/ingredients/low-stock', methods=['GET'])
def low_stock():
    rows = Ingredient.query.filter(Ingredient.current_stock < Ingredient.minimum_stock).all()
    return jsonify(IngredientSchema(many=True).dump(rows)), 200


@app.route('/ingredients/<int:id>/suppliers', methods=['GET'])
def ingredient_suppliers(id):
    rows = (db.session.query(Supplier.company, Supply.purchase_price, Supply.last_purchase_date)
            .join(Supply, Supply.supplier_id == Supplier.supplier_id)
            .filter(Supply.ingredient_id == id).all())
    return jsonify([{'company': r.company, 'purchase_price': float(r.purchase_price),
                     'last_purchase_date': r.last_purchase_date.isoformat()} for r in rows]), 200


# ======================================================================
# GUI: the page in static/index.html is served from the same server
# ======================================================================
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True, threaded=True)
