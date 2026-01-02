"""
Script de inicio optimizado para el ejecutable
Evita bucles infinitos y problemas de congelamiento
"""
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import sys
import pandas as pd
from utils.processing import (
    limpiar_inventario_csv, cargar_inventario_a_db,
    procesar_recetas_csv, cargar_recetas_a_db
)
from models import db, Producto, Receta, RecetaComponente
import webbrowser
import threading
import time

# Configurar rutas para PyInstaller
if getattr(sys, 'frozen', False):
    # Ejecutando como .exe
    bundle_dir = sys._MEIPASS
else:
    # Ejecutando como script
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

# Importar la app desde app.py
from app import app

def abrir_navegador():
    """Abre el navegador después de que el servidor esté listo"""
    time.sleep(1.5)  # Esperar a que el servidor inicie
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    # Prevenir múltiples ejecuciones
    multiprocessing_imported = False
    try:
        import multiprocessing
        multiprocessing.freeze_support()
        multiprocessing_imported = True
    except ImportError:
        pass
    
    # Configurar directorio de trabajo para el .exe
    if getattr(sys, 'frozen', False):
        # Si es .exe, usar el directorio donde está el .exe
        os.chdir(os.path.dirname(sys.executable))
        # Crear carpetas necesarias
        os.makedirs('instance', exist_ok=True)
        os.makedirs('uploads', exist_ok=True)
    
    # Crear las tablas si no existen
    with app.app_context():
        db.create_all()
    
    # Abrir navegador en un thread separado
    threading.Thread(target=abrir_navegador, daemon=True).start()
    
    print("=" * 60)
    print("AppLab iniciado correctamente!")
    print("Servidor corriendo en: http://127.0.0.1:5000")
    print("El navegador se abrirá automáticamente...")
    print("Presiona CTRL+C para detener el servidor")
    print("=" * 60)
    
    # Iniciar servidor sin debug mode ni reloader
    try:
        app.run(
            debug=False,
            use_reloader=False,
            host='127.0.0.1',
            port=5000,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\nServidor detenido correctamente")
        sys.exit(0)
