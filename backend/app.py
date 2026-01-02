from flask import  Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import pandas as pd
from utils.processing import (
    limpiar_inventario_csv, cargar_inventario_a_db,
    procesar_recetas_csv, cargar_recetas_a_db
)
from models import db, Producto, Receta, RecetaComponente

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'xls', 'xlsx', 'csv'}

db.init_app(app)

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
    productos = Producto.query.filter_by(is_master=False).all()
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
                resultado = cargar_inventario_a_db(filepath)
                flash(f'Stock cargado exitosamente: {resultado["productos_cargados"]} nuevos, {resultado["productos_actualizados"]} actualizados', 'success')
            elif tipo == 'recetas':
                resultado = cargar_recetas_a_db(filepath)
                flash(f'Recetas: procesadas {resultado["total_recetas_procesadas"]}, cargadas {resultado["recetas_cargadas"]}, componentes {resultado["total_componentes"]}, productos encontrados {resultado["productos_encontrados"]}, creados {resultado["productos_creados"]}', 'success')
            else:
                flash('Tipo de archivo no válido', 'danger')
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'danger')
        
        return redirect(url_for('cargar'))
    else:
        flash('Tipo de archivo no permitido', 'danger')
        return redirect(url_for('cargar'))

@app.route('/vaciar-recetas', methods=['POST'])
def vaciar_recetas():
    """Endpoint para vaciar todas las recetas y sus componentes"""
    try:
        num_recetas = Receta.query.count()
        num_componentes = RecetaComponente.query.count()
        
        # Eliminar recetas (esto también elimina componentes por cascade)
        Receta.query.delete()
        
        # Eliminar productos maestros que ya no tienen componentes asociados
        productos_maestros_huerfanos = Producto.query.filter_by(is_master=True).filter(
            ~Producto.id.in_(
                db.session.query(RecetaComponente.producto_id).distinct()
            )
        ).all()
        
        num_maestros_eliminados = len(productos_maestros_huerfanos)
        for producto in productos_maestros_huerfanos:
            db.session.delete(producto)
        
        db.session.commit()
        flash(f'Recetas vaciadas: {num_recetas} recetas, {num_componentes} componentes y {num_maestros_eliminados} productos maestros eliminados', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al vaciar recetas: {str(e)}', 'danger')
    
    return redirect(url_for('recetas'))

@app.route('/vaciar-stock', methods=['POST'])
def vaciar_stock():
    """Endpoint para vaciar todo el stock (elimina productos de stock, mantiene maestros)"""
    try:
        num_productos_eliminados = Producto.query.filter_by(is_master=False).delete()
        db.session.commit()
        flash(f'Stock vaciado: {num_productos_eliminados} productos de stock eliminados', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al vaciar stock: {str(e)}', 'danger')
    
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
        
        receta = db.session.get(Receta, receta_id)
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
        # Obtener el producto maestro o de receta
        producto_referencia = db.session.get(Producto, producto_id)
        
        if not producto_referencia:
            continue
        
        # Obtener todos los lotes del inventario con el mismo código, ordenados por vencimiento
        productos_stock = Producto.query.filter_by(
            codigo=producto_referencia.codigo,
            is_master=False  # Solo productos de stock (no maestros)
        ).order_by(Producto.fecha_vencimiento.asc()).all()
        
        # Calcular cantidad total disponible
        cantidad_disponible = sum(p.cantidad_disponible for p in productos_stock)
        
        if cantidad_disponible < cantidad_necesaria:
            puede_producir = False
            detalles.append({
                'producto': producto_referencia.nombre or producto_referencia.codigo,
                'necesario': cantidad_necesaria,
                'disponible': cantidad_disponible,
                'faltante': cantidad_necesaria - cantidad_disponible,
                'estado': 'insuficiente'
            })
        else:
            # Calcular qué lotes se usarán (FIFO por vencimiento)
            productos_a_usar = []
            cantidad_restante = cantidad_necesaria
            
            for producto in productos_stock:
                if cantidad_restante <= 0:
                    break
                
                cantidad_a_usar = min(producto.cantidad_disponible, cantidad_restante)
                productos_a_usar.append({
                    'lote': producto.lote or 'S/L',
                    'cantidad': cantidad_a_usar,
                    'vencimiento': producto.fecha_vencimiento.strftime('%Y-%m-%d') if producto.fecha_vencimiento else 'N/A'
                })
                cantidad_restante -= cantidad_a_usar
            
            detalles.append({
                'producto': producto_referencia.nombre or producto_referencia.codigo,
                'necesario': cantidad_necesaria,
                'disponible': cantidad_disponible,
                'lotes_a_usar': productos_a_usar,
                'estado': 'suficiente'
            })
    
    return jsonify({
        'puede_producir': puede_producir,
        'detalles': detalles
    })

@app.route('/resetear-db', methods=['POST'])
def resetear_db():
    """Endpoint para eliminar completamente la base de datos y reiniciarla"""
    try:
        # Eliminar todas las tablas
        db.drop_all()
        # Recrear todas las tablas
        db.create_all()
        flash('Base de datos reseteada completamente. Todas las recetas y productos han sido eliminados.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al resetear la base de datos: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Endpoint para cerrar el servidor de forma segura"""
    import os
    import signal
    
    # Enviar señal para cerrar el proceso
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({'status': 'Servidor cerrándose...'})




if __name__ == '__main__':
    import webbrowser
    import threading
    
    with app.app_context():
        db.create_all()
    
    def open_browser():
        webbrowser.open('http://127.0.0.1:5000')
    
    timer = threading.Timer(1.5, open_browser)
    timer.start()
    
    # Ejecutar Flask sin debug mode cuando es .exe
    app.run(debug=False, host='127.0.0.1', port=5000)
