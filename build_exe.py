"""
Script para compilar la aplicación como .exe para Windows usando PyInstaller
Ejecutar en Fedora: python build_exe.py
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
    'backend/app.py',                    # Script principal
    '--name=AppLab',                     # Nombre del ejecutable
    '--onefile',                         # Un solo archivo ejecutable
    '--windowed',                        # Sin consola (para GUI)
    '--add-data=backend/templates:templates',  # Incluir templates
    '--add-data=backend/utils:utils',          # Incluir utils
    '--hidden-import=flask',
    '--hidden-import=flask_sqlalchemy',
    '--hidden-import=sqlalchemy',
    '--hidden-import=pandas',
    '--hidden-import=openpyxl',          # Para leer Excel
    '--hidden-import=xlrd',              # Para leer XLS antiguos
    '--collect-all=flask',
    '--collect-all=sqlalchemy',
])

print("\n" + "="*50)
print("Compilación completada!")
print("El ejecutable está en: dist/AppLab.exe")
print("="*50)
