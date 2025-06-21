from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from datetime import datetime
import os
from werkzeug.utils import secure_filename


import os

# Caminho absoluto para garantir
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.secret_key = 'sua_chave_secreta_aqui'  # Troque por uma chave segura em produção
bcrypt = Bcrypt(app)

# Configurações
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Dados iniciais (em produção, use um banco de dados)
users = {
    'admin': {
        'password': bcrypt.generate_password_hash('admin123').decode('utf-8'),
        'name': 'Administrador'
    }
}

products = {
    'hamburgueres': [
        {'id': 1, 'name': "Hambúrguer Clássico", 'price': 20.00, 'description': "Pão, carne, queijo e salada", 'image': "Hambúrguer Clássico.jpeg", 'stock': 50},
        {'id': 2, 'name': "Cheeseburguer", 'price': 22.00, 'description': "Com queijo derretido", 'image': "cheeseburguer.jpeg", 'stock': 45},
    ],
    'bebidas': [
        {'id': 6, 'name': "Refrigerante", 'price': 6.00, 'description': "Lata 350ml", 'image': "Refrigerante.jpeg", 'stock': 100},
    ]
}

orders = []
sales_data = {'total': 0, 'monthly': {}, 'daily': {}}

# Funções auxiliares
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_next_id(category):
    if not products.get(category):
        return 1
    return max(p['id'] for p in products[category]) + 1

# Rotas públicas
@app.route('/')
def index():
    return render_template('index.html', products=products)

# Rotas de autenticação
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = users.get(username)
        if user and bcrypt.check_password_hash(user['password'], password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Usuário ou senha incorretos', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('Você foi desconectado', 'info')
    return redirect(url_for('admin_login'))

# Middleware para proteger rotas administrativas
@app.before_request
def require_admin_login():
    admin_routes = ['admin_dashboard', 'admin_products', 'admin_orders', 'admin_inventory']
    if request.endpoint in admin_routes and not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

# Rotas administrativas
@app.route('/admin/dashboard')
def admin_dashboard():
    # Estatísticas para o dashboard
    stats = {
        'total_products': sum(len(category) for category in products.values()),
        'total_orders': len(orders),
        'total_sales': sales_data['total'],
        'recent_orders': orders[-5:][::-1] if orders else []
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/products', methods=['GET', 'POST'])
def admin_products():
    if request.method == 'POST':
        # Adicionar novo produto
        category = request.form.get('category')
        name = request.form.get('name')
        price = float(request.form.get('price'))
        description = request.form.get('description')
        stock = int(request.form.get('stock', 0))
        
        # Upload da imagem
        image_file = request.files.get('image')
        filename = None
        
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        new_product = {
            'id': get_next_id(category),
            'name': name,
            'price': price,
            'description': description,
            'image': filename if filename else 'default-product.png',
            'stock': stock
        }
        
        if category not in products:
            products[category] = []
        products[category].append(new_product)
        
        flash('Produto adicionado com sucesso!', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/delete/<category>/<int:product_id>')
def delete_product(category, product_id):
    if category in products:
        products[category] = [p for p in products[category] if p['id'] != product_id]
        flash('Produto removido com sucesso!', 'success')
    else:
        flash('Categoria não encontrada', 'danger')
    
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
def admin_orders():
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/orders/update/<int:order_id>/<status>')
def update_order_status(order_id, status):
    for order in orders:
        if order['id'] == order_id:
            order['status'] = status
            order['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            flash('Status do pedido atualizado!', 'success')
            break
    
    return redirect(url_for('admin_orders'))

@app.route('/admin/inventory')
def admin_inventory():
    # Calcular valor total do estoque
    total_value = 0
    for category in products.values():
        for product in category:
            total_value += product['price'] * product['stock']
    
    return render_template('admin/inventory.html', products=products, total_value=total_value)

@app.route('/admin/inventory/update', methods=['POST'])
def update_inventory():
    for category in products:
        for product in products[category]:
            stock_key = f"stock_{category}_{product['id']}"
            new_stock = request.form.get(stock_key)
            if new_stock:
                product['stock'] = int(new_stock)
    
    flash('Estoque atualizado com sucesso!', 'success')
    return redirect(url_for('admin_inventory'))

# API para receber pedidos do frontend
@app.route('/api/place_order', methods=['POST'])
def place_order():
    if not request.is_json:
        return {'error': 'Invalid request'}, 400
    
    data = request.get_json()
    
    # Criar novo pedido
    new_order = {
        'id': len(orders) + 1,
        'customer_name': data.get('customer_name'),
        'customer_address': data.get('customer_address'),
        'customer_phone': data.get('customer_phone'),
        'items': data.get('items', []),
        'total': data.get('total'),
        'payment_method': data.get('payment_method'),
        'status': 'Recebido',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Atualizar estoque
    for item in new_order['items']:
        for category in products.values():
            for product in category:
                if product['id'] == item['id']:
                    product['stock'] -= item['quantity']
                    break
    
    # Registrar venda
    orders.append(new_order)
    sales_data['total'] += new_order['total']
    
    today = datetime.now().strftime('%Y-%m-%d')
    if today not in sales_data['daily']:
        sales_data['daily'][today] = 0
    sales_data['daily'][today] += new_order['total']
    
    month = datetime.now().strftime('%Y-%m')
    if month not in sales_data['monthly']:
        sales_data['monthly'][month] = 0
    sales_data['monthly'][month] += new_order['total']
    
    return {'success': True, 'order_id': new_order['id']}

if __name__ == '__main__':
    app.run(debug=True)