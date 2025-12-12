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
        
        # Usar codigo_receta como nombre
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