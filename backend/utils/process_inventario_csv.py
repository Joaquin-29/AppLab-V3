import pandas as pd
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import db, Producto

def limpiar_inventario_csv(csv_path):
    """
    Lee un archivo CSV de inventario y limpia las filas que no son productos.
    Retorna un DataFrame limpio con solo los productos.
    """
    # Leer el CSV
    df = pd.read_csv(csv_path)
    
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
    df_productos.columns = ['col0', 'codigo', 'col2', 'nombre', 'lote', 'vencimiento', 
                           'estado', 'unidad', 'cantidad', 'total']
    
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


def cargar_inventario_a_db(csv_path):
    """
    Procesa un archivo CSV de inventario y carga los productos en la base de datos.
    """
    # Limpiar y procesar el CSV
    df_productos = limpiar_inventario_csv(csv_path)
    
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
                fecha_vencimiento=row['vencimiento']
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


if __name__ == "__main__":
    # Ejemplo de uso - necesita contexto de Flask
    from app import app
    
    csv_path = "/home/kerberos/Codigo/AppLab-V3/uploads/inventario.csv"
    
    with app.app_context():
        # Crear las tablas si no existen
        db.create_all()
        
        resultado = cargar_inventario_a_db(csv_path)
        print(f"Productos cargados: {resultado['productos_cargados']}")
        print(f"Productos actualizados: {resultado['productos_actualizados']}")
        print(f"Total: {resultado['total']}")
