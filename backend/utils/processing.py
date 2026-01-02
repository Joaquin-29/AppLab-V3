import pandas as pd
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import db, Producto, Receta, RecetaComponente

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
            lote=row['lote'],
            is_master=False  # Solo buscar en productos de stock
        ).first()
        
        if producto_existente:
            # Actualizar el producto existente
            producto_existente.nombre = row['nombre']
            producto_existente.unidad = row['unidad_normalizada']
            producto_existente.cantidad_disponible = row['cantidad_normalizada']
            producto_existente.fecha_vencimiento = row['vencimiento']
            productos_actualizados += 1
        else:
            # Verificar si existe un producto maestro con el mismo código
            producto_maestro = Producto.query.filter_by(
                codigo=row['codigo'],
                is_master=True
            ).first()
            
            if producto_maestro and not producto_maestro.nombre:
                # Actualizar el nombre del producto maestro si estaba vacío
                producto_maestro.nombre = row['nombre']
            
            # Crear un nuevo producto de stock
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


def procesar_recetas_csv(file_path):
    """
    Lee un archivo CSV o XLS de recetas y lo procesa.
    Estructura del archivo:
    - Receta: Col[1]="Artículo", Col[2]=código, Col[5]=nombre
    - Componentes: Col[1]=número_paso, Col[12]=código, Col[14]=nombre, Col[16]=unidad, Col[17]=cantidad
    """
    # Leer el archivo según su extensión
    if file_path.lower().endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file_path, engine='xlrd' if file_path.lower().endswith('.xls') else None, header=None)
    else:
        df = pd.read_csv(file_path, header=None)
    
    recetas_dict = {}
    codigo_receta_actual = None
    nombre_receta_actual = None
    
    for idx, row in df.iterrows():
        # Verificar si esta fila define una nueva receta (tiene "Artículo" en columna 1)
        if len(row) > 5 and pd.notna(row[1]) and 'artículo' in str(row[1]).lower():
            # El código está en columna 2, nombre en columna 5
            codigo = str(row[2]).strip() if pd.notna(row[2]) else None
            nombre = str(row[5]).strip() if pd.notna(row[5]) else None
            
            # Validar que el código parece válido
            if codigo and codigo != 'nan' and any(c.isdigit() for c in codigo):
                codigo_receta_actual = codigo
                nombre_receta_actual = nombre if nombre and nombre != 'nan' else codigo
                
                if codigo_receta_actual not in recetas_dict:
                    recetas_dict[codigo_receta_actual] = {
                        'nombre': nombre_receta_actual,
                        'componentes': []
                    }
        
        # Verificar si es una fila de componente
        # Debe tener un número en col[1] (paso), datos en col[12] (código) y col[17] (cantidad)
        elif codigo_receta_actual and len(row) > 17:
            col_paso = str(row[1]).strip() if pd.notna(row[1]) else ''
            col_codigo_comp = str(row[12]).strip() if pd.notna(row[12]) else ''
            col_nombre_comp = str(row[14]).strip() if pd.notna(row[14]) else ''
            col_unidad = str(row[16]).strip() if pd.notna(row[16]) else ''
            col_cantidad = row[17] if pd.notna(row[17]) else None
            
            # Verificar que es una fila de componente válida
            # Col[1] debe ser un número (paso)
            # Col[12] debe tener código de componente
            # Col[17] debe tener cantidad
            if (col_paso.isdigit() and 
                col_codigo_comp and 
                col_codigo_comp != 'nan' and
                col_cantidad is not None):
                
                try:
                    # Convertir cantidad
                    if isinstance(col_cantidad, str):
                        cantidad = float(col_cantidad.replace(',', '.').replace(' ', ''))
                    else:
                        cantidad = float(col_cantidad)
                    
                    # Normalizar unidad
                    unidad = normalizar_unidad(col_unidad) if col_unidad and col_unidad != 'nan' else 'uni'
                    
                    # Agregar componente
                    recetas_dict[codigo_receta_actual]['componentes'].append({
                        'codigo_producto': col_codigo_comp,
                        'nombre_producto': col_nombre_comp if col_nombre_comp and col_nombre_comp != 'nan' else col_codigo_comp,
                        'cantidad': cantidad,
                        'unidad': unidad
                    })
                except (ValueError, AttributeError) as e:
                    # Si no se puede convertir la cantidad, ignorar esta línea
                    pass
    
    # Filtrar recetas vacías
    recetas_dict = {k: v for k, v in recetas_dict.items() if v['componentes']}
    
    return recetas_dict, [], {}


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
        
        if receta_existente:
            # Si la receta ya existe, eliminar sus componentes antiguos para recargarlos
            RecetaComponente.query.filter_by(receta_id=receta_existente.id).delete()
            db.session.flush()  # Asegurar que la eliminación se aplique antes de agregar nuevos
            receta = receta_existente
        else:
            # Crear nueva receta
            receta = Receta(
                codigo=codigo_receta,
                nombre=data['nombre']
            )
            db.session.add(receta)
            db.session.flush()  # Para obtener el ID
        
        # Agregar componentes
        componentes_agregados = 0
        for comp in data['componentes']:
            codigo_producto = comp['codigo_producto'].strip()
            nombre_producto = comp.get('nombre_producto', codigo_producto)
            
            # Buscar el producto primero por código exacto (case insensitive)
            producto = Producto.query.filter(Producto.codigo.ilike(codigo_producto)).first()
            
            # Si no se encuentra por código, buscar por nombre exacto
            if not producto and nombre_producto:
                producto = Producto.query.filter(Producto.nombre.ilike(nombre_producto)).first()
            
            if not producto:
                # Crear el producto maestro si no existe
                producto = Producto(
                    codigo=codigo_producto,
                    nombre=nombre_producto,  # Usar el nombre del archivo o el código
                    unidad=comp['unidad'],
                    cantidad_disponible=0,  # Sin stock inicialmente
                    fecha_vencimiento=None,
                    lote=None,
                    is_master=True  # Producto maestro creado desde recetas
                )
                db.session.add(producto)
                db.session.flush()  # Para obtener el ID
            
            componente = RecetaComponente(
                receta_id=receta.id,
                producto_id=producto.id,
                cantidad_necesaria=comp['cantidad'],
                unidad=comp['unidad']
            )
            db.session.add(componente)
            componentes_agregados += 1
        
        if componentes_agregados > 0:
            recetas_cargadas += 1
        elif not receta_existente:
            # Si no se agregaron componentes y es nueva, eliminar la receta
            db.session.delete(receta)
    
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