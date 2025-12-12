from flask import  Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import pandas as pd

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
    is_master = db.Column(db.Boolean, default=False)  # True para productos maestros (de recetas), False para stock

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

# ==================== FUNCIONES DE PROCESAMIENTO ====================

def limpiar_inventario_csv(file_path):
    """
    Lee un archivo CSV o XLS de inventario y limpia las filas que no son productos.
    Retorna un DataFrame limpio con solo los productos.
    """
    # Leer el archivo según su extensión
    if file_path.lower().endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file_path, engine='xlrd' if file_path.lower().endswith('.xls') else None)
    else:
        df = pd.read_csv(file_path)
    
    # Identificar las filas que contienen productos
    # Los productos tienen un código de artículo en la segunda columna
    # y suelen tener datos en las columnas de Lote, Vto., etc.
    
    # Encontrar la fila donde empieza la tabla de productos (contiene "Artículo")
    start_idx = None
    for idx, row in df.iterrows():
        if 'Artículo' in str(row.values):
            start_idx = idx + 1
            break
    
    if start_idx is None:
        raise ValueError("No se encontró el inicio de la tabla de productos en el CSV")
    
    # Filtrar solo las filas desde donde empiezan los productos
    df_productos = df.iloc[start_idx:].copy()
    
    # Renombrar columnas para facilitar el trabajo
    # Basándonos en la estructura: Artículo, nombre, Lote, Vto., Estado, Unidad, Cantidad, Total
    num_cols = len(df_productos.columns)
    if num_cols >= 10:
        df_productos.columns = ['col0', 'codigo', 'col2', 'nombre', 'lote', 'vencimiento', 
                               'estado', 'unidad', 'cantidad', 'total'] + [f'col{i}' for i in range(10, num_cols)]
    else:
        # Si hay menos columnas, ajustar
        default_cols = ['col0', 'codigo', 'col2', 'nombre', 'lote', 'vencimiento', 
                       'estado', 'unidad', 'cantidad', 'total']
        df_productos.columns = default_cols[:num_cols]
    
    # Filtrar filas que tienen código de artículo (no vacías)
    df_productos = df_productos[df_productos['codigo'].notna()].copy()
    
    # Limpiar espacios en blanco en código
    df_productos['codigo'] = df_productos['codigo'].astype(str).str.strip()
    
    # Convertir fecha de vencimiento a datetime
    df_productos['vencimiento'] = pd.to_datetime(df_productos['vencimiento'], errors='coerce')
    
    # Convertir cantidad a float
    df_productos['cantidad'] = pd.to_numeric(df_productos['cantidad'], errors='coerce')
    
    # Eliminar filas sin cantidad válida
    df_productos = df_productos[df_productos['cantidad'].notna()].copy()
    
    # Normalizar unidades de medida
    df_productos['unidad'] = df_productos['unidad'].astype(str).str.strip()
    df_productos['unidad_normalizada'] = df_productos['unidad'].apply(normalizar_unidad)
    df_productos['cantidad_normalizada'] = df_productos.apply(
        lambda row: convertir_cantidad(row['cantidad'], row['unidad'], row['unidad_normalizada']), 
        axis=1
    )
    
    return df_productos[['codigo', 'nombre', 'lote', 'vencimiento', 'estado', 
                        'unidad_normalizada', 'cantidad_normalizada']]


def normalizar_unidad(unidad):
    """
    Normaliza las unidades de medida a un formato estándar.
    Convierte todo a gramos (g) o litros (L).
    """
    unidad = str(unidad).strip().lower()
    
    # Mapeo de unidades
    if unidad in ['kg', 'kilo', 'kilogramo']:
        return 'g'
    elif unidad in ['l', 'litro', 'litros']:
        return 'L'
    elif unidad in ['g', 'gr', 'gramo', 'gramos']:
        return 'g'
    elif unidad in ['ml', 'mililitro', 'mililitros']:
        return 'L'
    elif unidad in ['uni', 'unidad', 'unidades', 'u']:
        return 'uni'
    else:
        return unidad


def convertir_cantidad(cantidad, unidad_original, unidad_destino):
    """
    Convierte la cantidad de una unidad a otra.
    """
    unidad_original = str(unidad_original).strip().lower()
    
    # Si la unidad original es Kg y la destino es g, multiplicar por 1000
    if unidad_original in ['kg', 'kilo'] and unidad_destino == 'g':
        return cantidad * 1000
    
    # Si la unidad original es mL y la destino es L, dividir por 1000
    if unidad_original in ['ml', 'mililitro'] and unidad_destino == 'L':
        return cantidad / 1000
    
    # Si no hay conversión necesaria, retornar la cantidad original
    return cantidad


def cargar_inventario_a_db(file_path):
    """
    Procesa un archivo de inventario y carga los productos en la base de datos.
    """
    # Limpiar y procesar el archivo
    df_productos = limpiar_inventario_csv(file_path)
    
    productos_cargados = 0
    productos_actualizados = 0
    
    for _, row in df_productos.iterrows():
        # Buscar si el producto ya existe por código y lote
        producto_existente = Producto.query.filter_by(
            codigo=row['codigo'], 
            lote=row['lote']
        ).first()
        
        if producto_existente:
            # Actualizar el producto existente
            producto_existente.nombre = row['nombre']
            producto_existente.unidad = row['unidad_normalizada']
            producto_existente.cantidad_disponible = row['cantidad_normalizada']
            producto_existente.fecha_vencimiento = row['vencimiento']
            productos_actualizados += 1
        else:
            # Crear un nuevo producto
            nuevo_producto = Producto(
                codigo=row['codigo'],
                nombre=row['nombre'],
                lote=row['lote'],
                unidad=row['unidad_normalizada'],
                cantidad_disponible=row['cantidad_normalizada'],
                fecha_vencimiento=row['vencimiento'],
                is_master=False  # Producto de stock
            )
            db.session.add(nuevo_producto)
            productos_cargados += 1
    
    # Guardar los cambios en la base de datos
    db.session.commit()
    
    return {
        'productos_cargados': productos_cargados,
        'productos_actualizados': productos_actualizados,
        'total': productos_cargados + productos_actualizados
    }

# ==================== FUNCIONES DE RECETAS ====================

def procesar_recetas_csv(file_path):
    """
    Lee un archivo CSV o XLS de recetas y lo procesa.
    Busca la fila de encabezados y procesa desde ahí.
    """
    # Leer el archivo según su extensión
    if file_path.lower().endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file_path, engine='xlrd' if file_path.lower().endswith('.xls') else None, header=None)
    else:
        df = pd.read_csv(file_path, header=None)
    
    # Encontrar la fila de encabezados (contiene 'artículo' o 'componente')
    header_idx = None
    for idx, row in df.iterrows():
        row_str = str(row.values).lower()
        if 'artículo' in row_str or 'componente' in row_str:
            header_idx = idx
            break
    
    if header_idx is None:
        # Si no encuentra, asumir primera fila
        header_idx = 0
    
    # Usar la fila de encabezados como header
    df = df.iloc[header_idx:].reset_index(drop=True)
    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)
    
    # Normalizar nombres de columnas a minúsculas y quitar espacios
    df.columns = df.columns.str.strip().str.lower()
    
    # Mapear columnas basadas en el contenido
    col_map = {
        'codigo_receta': None,
        'codigo_producto': None,
        'cantidad': None,
        'unidad': None
    }
    
    for col in df.columns:
        col_str = str(col).lower()
        if 'artículo' in col_str:
            col_map['codigo_receta'] = col
        elif 'componente' in col_str:
            col_map['codigo_producto'] = col
        elif 'cantidad' in col_str:
            col_map['cantidad'] = col
        elif 'unidad' in col_str:
            col_map['unidad'] = col
    
    # Si no se encontraron, asumir posiciones
    if not all(col_map.values()):
        if len(df.columns) >= 4:
            col_map = {
                'codigo_receta': df.columns[0],
                'codigo_producto': df.columns[1],
                'unidad': df.columns[2],
                'cantidad': df.columns[3]
            }
    
    # Agrupar por receta
    recetas_dict = {}
    
    for _, row in df.iterrows():
        codigo_receta = str(row.get(col_map.get('codigo_receta', ''), '')).strip()
        codigo_producto = str(row.get(col_map.get('codigo_producto', ''), '')).strip()
        cantidad = pd.to_numeric(str(row.get(col_map.get('cantidad', ''), '')).replace(',', '.'), errors='coerce')
        unidad = str(row.get(col_map.get('unidad', ''), '')).strip()
        
        if not codigo_receta or not codigo_producto or pd.isna(cantidad) or not codigo_producto.strip():
            continue
        
        # Usar codigo_receta como nombre también
        nombre_receta = codigo_receta
        
        if codigo_receta not in recetas_dict:
            recetas_dict[codigo_receta] = {
                'nombre': nombre_receta,
                'componentes': []
            }
        
        recetas_dict[codigo_receta]['componentes'].append({
            'codigo_producto': codigo_producto,
            'cantidad': cantidad,
            'unidad': unidad
        })
    
    return recetas_dict, list(df.columns), col_map


def cargar_recetas_a_db(file_path):
    """
    Procesa un archivo de recetas y carga las recetas y componentes en la base de datos.
    """
    recetas_dict, columns, col_map = procesar_recetas_csv(file_path)
    
    # Debug info
    total_recetas_procesadas = len(recetas_dict)
    total_componentes = sum(len(data['componentes']) for data in recetas_dict.values())
    
    productos_encontrados = 0
    productos_creados = 0
    
    for data in recetas_dict.values():
        for comp in data['componentes']:
            producto = Producto.query.filter(
                (Producto.codigo.ilike(comp['codigo_producto'])) | 
                (Producto.nombre.ilike(comp['codigo_producto']))
            ).first()
            if producto:
                productos_encontrados += 1
            else:
                productos_creados += 1
    
    recetas_cargadas = 0
    
    for codigo_receta, data in recetas_dict.items():
        # Verificar si la receta ya existe
        receta_existente = Receta.query.filter_by(codigo=codigo_receta).first()
        
        if not receta_existente:
            # Crear nueva receta
            nueva_receta = Receta(
                codigo=codigo_receta,
                nombre=data['nombre']
            )
            db.session.add(nueva_receta)
            db.session.flush()  # Para obtener el ID
            
            # Agregar componentes
            componentes_agregados = 0
            for comp in data['componentes']:
                # Buscar el producto por código o nombre (case insensitive)
                producto = Producto.query.filter(
                    (Producto.codigo.ilike(comp['codigo_producto'])) | 
                    (Producto.nombre.ilike(comp['codigo_producto']))
                ).first()
                
                if not producto:
                    # Crear el producto si no existe
                    producto = Producto(
                        codigo=comp['codigo_producto'],
                        nombre=comp['codigo_producto'],  # Usar el mismo como nombre
                        unidad=comp['unidad'],
                        cantidad_disponible=0,  # Sin stock inicialmente
                        fecha_vencimiento=None,
                        lote=None,
                        is_master=True  # Producto maestro creado desde recetas
                    )
                    db.session.add(producto)
                    db.session.flush()  # Para obtener el ID
                
                componente = RecetaComponente(
                    receta_id=nueva_receta.id,
                    producto_id=producto.id,
                    cantidad_necesaria=comp['cantidad'],
                    unidad=comp['unidad']
                )
                db.session.add(componente)
                componentes_agregados += 1
            
            if componentes_agregados > 0:
                recetas_cargadas += 1
            else:
                # Si no se agregaron componentes, eliminar la receta
                db.session.delete(nueva_receta)
    
    db.session.commit()
    
    return {
        'recetas_cargadas': recetas_cargadas,
        'total_recetas_procesadas': total_recetas_procesadas,
        'total_componentes': total_componentes,
        'productos_encontrados': productos_encontrados,
        'productos_creados': productos_creados,
        'columnas_detectadas': columns,
        'mapeo_columnas': col_map
    }

# ==================== FIN FUNCIONES ====================

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
    """Endpoint para vaciar todas las recetas"""
    try:
        num_recetas = Receta.query.count()
        Receta.query.delete()  # Esto debería eliminar recetas y componentes por cascade
        db.session.commit()
        flash(f'Recetas vaciadas: {num_recetas} recetas eliminadas', 'success')
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
        # Obtener todos los lotes del producto ordenados por fecha de vencimiento
        productos = Producto.query.filter_by(codigo=db.session.get(Producto, producto_id).codigo)\
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