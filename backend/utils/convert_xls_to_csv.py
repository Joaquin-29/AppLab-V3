import pandas as pd

# Nombre del archivo XLS (ajusta la ruta si es necesario)
xls_file = 'uploads/ME 08 01 2024.xls'

# Nombre del archivo CSV de salida
csv_file = 'ME 08 01 2024.csv'

try:
    df = pd.read_excel(xls_file, engine='xlrd')
    
    df.to_csv(csv_file, index=False, encoding='utf-8')
    
    print(f"Conversión exitosa: {xls_file} -> {csv_file}")
    print(f"Filas: {len(df)}, Columnas: {len(df.columns)}")
    
except Exception as e:
    print(f"Error durante la conversión: {e}")