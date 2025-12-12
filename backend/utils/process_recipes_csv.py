import pandas as pd
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import db, Receta, RecetaComponente, Producto


def procesar_recetas_csv(file_path):
    """
    Lee un archivo CSV o XLS de recetas y lo procesa.
    El formato esperado es un archivo con las siguientes columnas:
    - Código de receta
    - Nombre de receta
    - Código de componente/producto
    - Cantidad necesaria
    - Unidad
    """
    # Leer el archivo según su extensión
    if file_path.lower().endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file_path, engine='xlrd' if file_path.lower().endswith('.xls') else None)
    else:
        df = pd.read_csv(file_path)
    
    # Agrupar por receta
    recetas_dict = {}
    
    for _, row in df.iterrows():
        codigo_receta = str(row.get('codigo_receta', '')).strip()
        nombre_receta = str(row.get('nombre_receta', '')).strip()
        codigo_producto = str(row.get('codigo_producto', '')).strip()
        cantidad = float(row.get('cantidad', 0))
        unidad = str(row.get('unidad', '')).strip()
        
        if not codigo_receta or not codigo_producto:
            continue
        
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
    
    return recetas_dict


def cargar_recetas_a_db(csv_path):
    """
    Procesa un archivo CSV de recetas y las carga en la base de datos.
    """
    recetas_dict = procesar_recetas_csv(csv_path)
    
    recetas_cargadas = 0
    
    for codigo, data in recetas_dict.items():
        # Verificar si la receta ya existe
        receta_existente = Receta.query.filter_by(codigo=codigo).first()
        
        if receta_existente:
            # Actualizar receta existente
            receta = receta_existente
            receta.nombre = data['nombre']
            # Eliminar componentes existentes
            RecetaComponente.query.filter_by(receta_id=receta.id).delete()
        else:
            # Crear nueva receta
            receta = Receta(
                codigo=codigo,
                nombre=data['nombre']
            )
            db.session.add(receta)
            db.session.flush()  # Para obtener el ID de la receta
            recetas_cargadas += 1
        
        # Agregar componentes
        for comp in data['componentes']:
            # Buscar el producto por código
            producto = Producto.query.filter_by(codigo=comp['codigo_producto']).first()
            
            if not producto:
                # Si el producto no existe, crearlo con valores mínimos
                producto = Producto(
                    codigo=comp['codigo_producto'],
                    nombre=comp['codigo_producto'],  # Usar el código como nombre temporal
                    unidad=comp['unidad'],
                    cantidad_disponible=0
                )
                db.session.add(producto)
                db.session.flush()
            
            # Crear el componente de la receta
            componente = RecetaComponente(
                receta_id=receta.id,
                producto_id=producto.id,
                cantidad_necesaria=comp['cantidad'],
                unidad=comp['unidad']
            )
            db.session.add(componente)
        
    db.session.commit()
    
    return {
        'recetas_cargadas': recetas_cargadas
    }