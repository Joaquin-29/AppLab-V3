from flask import  Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'xls', 'xlsx', 'csv'}

db = SQLAlchemy(app)

# ==================== MODELOS ====================
class Producto(db.Model):
    __tablename__ = 'productos'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    unidad = db.Column(db.String(20), nullable=False)
    cantidad_disponible = db.Column(db.Float, nullable=False, default=0)
    fecha_vencimiento = db.Column(db.DateTime, nullable=True)
    lote = db.Column(db.String(50), nullable=True)

    componentes = db.relationship('RecetaComponente', back_populates='producto')

    def __repr__(self):
        return f'<Producto {self.nombre}>'

class Receta(db.Model):
    __tablename__ = 'recetas'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)

    componentes = db.relationship('RecetaComponente', back_populates='receta', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Receta {self.nombre}>'

class RecetaComponente(db.Model):
    __tablename__ = 'receta_componentes'
    
    id = db.Column(db.Integer, primary_key=True)
    receta_id = db.Column(db.Integer, db.ForeignKey('recetas.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad_necesaria = db.Column(db.Float, nullable=False)
    unidad = db.Column(db.String(20), nullable=False)

    receta = db.relationship('Receta', back_populates='componentes')
    producto = db.relationship('Producto', back_populates='componentes')

    def __repr__(self):
        return f'<RecetaComponente RecetaID: {self.receta_id}, ProductoID: {self.producto_id}, Cantidad: {self.cantidad_necesaria} {self.unidad}>'

# ==================== FIN MODELOS ====================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cargar')
def cargar():
    """Página para cargar archivos de stock o recetas"""
    return render_template('cargar.html')

@app.route('/stock')
def stock():
    """Página para visualizar el stock"""
    productos = Producto.query.all()
    return render_template('stock.html', productos=productos, now=datetime.now)

@app.route('/recetas')
def recetas():
    """Página para visualizar las recetas"""
    recetas_list = Receta.query.all()
    return render_template('recetas.html', recetas=recetas_list)

@app.route('/produccion')
def produccion():
    """Página para calcular la producción"""
    recetas_list = Receta.query.all()
    return render_template('produccion.html', recetas=recetas_list)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Endpoint para subir archivos"""
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'danger')
        return redirect(url_for('cargar'))
    
    file = request.files['file']
    tipo = request.form.get('tipo')  # 'stock' o 'recetas'
    
    if file.filename == '':
        flash('No se seleccionó ningún archivo', 'danger')
        return redirect(url_for('cargar'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Procesar el archivo según el tipo
        try:
            if tipo == 'stock':
                import sys
                sys.path.insert(0, os.path.dirname(__file__))
                from utils.process_inventario_csv import cargar_inventario_a_db
                resultado = cargar_inventario_a_db(filepath)
                flash(f'Stock cargado exitosamente: {resultado["productos_cargados"]} nuevos, {resultado["productos_actualizados"]} actualizados', 'success')
            elif tipo == 'recetas':
                import sys
                sys.path.insert(0, os.path.dirname(__file__))
                from utils.process_recipes_csv import cargar_recetas_a_db
                resultado = cargar_recetas_a_db(filepath)
                flash(f'Recetas cargadas exitosamente: {resultado["recetas_cargadas"]} nuevas', 'success')
            else:
                flash('Tipo de archivo no válido', 'danger')
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'danger')
        
        return redirect(url_for('cargar'))
    else:
        flash('Tipo de archivo no permitido', 'danger')
        return redirect(url_for('cargar'))

@app.route('/vaciar-stock', methods=['POST'])
def vaciar_stock():
    """Endpoint para vaciar todo el stock"""
    try:
        num_productos = Producto.query.count()
        Producto.query.delete()
        db.session.commit()
        flash(f'Se eliminaron {num_productos} productos del inventario', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al vaciar el stock: {str(e)}', 'danger')
    return redirect(url_for('stock'))

@app.route('/calcular-produccion', methods=['POST'])
def calcular_produccion():
    """Endpoint para calcular si se puede producir las recetas seleccionadas"""
    data = request.get_json()
    recetas_seleccionadas = data.get('recetas', [])
    
    resultados = []
    productos_necesarios = {}
    
    # Calcular la cantidad total de cada producto necesario
    for receta_data in recetas_seleccionadas:
        receta_id = receta_data['id']
        cantidad = receta_data['cantidad']
        
        receta = Receta.query.get(receta_id)
        if not receta:
            continue
        
        for componente in receta.componentes:
            producto_id = componente.producto_id
            cantidad_necesaria = componente.cantidad_necesaria * cantidad
            
            if producto_id in productos_necesarios:
                productos_necesarios[producto_id] += cantidad_necesaria
            else:
                productos_necesarios[producto_id] = cantidad_necesaria
    
    # Verificar disponibilidad de cada producto
    puede_producir = True
    detalles = []
    
    for producto_id, cantidad_necesaria in productos_necesarios.items():
        # Obtener todos los lotes del producto ordenados por fecha de vencimiento
        productos = Producto.query.filter_by(codigo=Producto.query.get(producto_id).codigo)\
                                   .order_by(Producto.fecha_vencimiento)\
                                   .all()
        
        cantidad_disponible = sum(p.cantidad_disponible for p in productos)
        
        if cantidad_disponible < cantidad_necesaria:
            puede_producir = False
            detalles.append({
                'producto': productos[0].nombre if productos else 'Desconocido',
                'necesario': cantidad_necesaria,
                'disponible': cantidad_disponible,
                'faltante': cantidad_necesaria - cantidad_disponible,
                'estado': 'insuficiente'
            })
        else:
            # Verificar vencimientos
            productos_a_usar = []
            cantidad_restante = cantidad_necesaria
            
            for producto in productos:
                if cantidad_restante <= 0:
                    break
                
                cantidad_a_usar = min(producto.cantidad_disponible, cantidad_restante)
                productos_a_usar.append({
                    'lote': producto.lote,
                    'cantidad': cantidad_a_usar,
                    'vencimiento': producto.fecha_vencimiento.strftime('%Y-%m-%d') if producto.fecha_vencimiento else 'N/A'
                })
                cantidad_restante -= cantidad_a_usar
            
            detalles.append({
                'producto': productos[0].nombre,
                'necesario': cantidad_necesaria,
                'disponible': cantidad_disponible,
                'lotes_a_usar': productos_a_usar,
                'estado': 'suficiente'
            })
    
    return jsonify({
        'puede_producir': puede_producir,
        'detalles': detalles
    })







if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    app.run(debug=True)