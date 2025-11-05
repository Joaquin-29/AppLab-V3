import pandas as pd

# Nombre del archivo XLS (ajusta la ruta si es necesario)
xls_file = 'MP 05 11 2025.xls'

# Nombre del archivo CSV de salida
csv_file = 'MP 05 11 2025.csv'

try:
    # Leer el archivo XLS (primera hoja por defecto)
    df = pd.read_excel(xls_file, engine='xlrd')
    
    # Guardar como CSV
    df.to_csv(csv_file, index=False, encoding='utf-8')
    
    print(f"Conversión exitosa: {xls_file} -> {csv_file}")
    print(f"Filas: {len(df)}, Columnas: {len(df.columns)}")
    
except Exception as e:
    print(f"Error durante la conversión: {e}")