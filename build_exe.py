"""
Script para compilar la aplicación como .exe para Windows usando PyInstaller
Ejecutar: python build_exe.py
"""

import PyInstaller.__main__
import os
import shutil

# Limpiar builds anteriores
if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')

# Configuración de PyInstaller
PyInstaller.__main__.run([
    'backend/run_exe.py',                          # Script principal optimizado para ejecutables
    '--name=AppLab',                               # Nombre del ejecutable
    '--onefile',                                   # Un solo archivo ejecutable
    '--console',                                   # CON consola para ver logs/errores
    '--add-data=backend/templates:templates',      # Incluir templates
    '--add-data=backend/instance:instance',        # Incluir carpeta de BD
    '--add-data=uploads:uploads',                  # Incluir carpeta uploads
    '--hidden-import=flask',
    '--hidden-import=flask_sqlalchemy',
    '--hidden-import=sqlalchemy',
    '--hidden-import=pandas',
    '--hidden-import=openpyxl',                    # Para leer Excel
    '--hidden-import=xlrd',                        # Para leer XLS antiguos
    '--hidden-import=werkzeug',
    '--hidden-import=jinja2',
    '--hidden-import=webbrowser',                  # Para abrir navegador
    '--hidden-import=threading',                   # Para threads
    '--collect-all=flask',
    '--collect-all=sqlalchemy',
    '--copy-metadata=flask',
    '--copy-metadata=werkzeug',
])

print("\n" + "="*50)
print("Compilación completada!")
print("El ejecutable está en: dist/AppLab.exe")
print("NOTA: Ejecuta el .exe desde la terminal para ver logs")
print("="*50)
