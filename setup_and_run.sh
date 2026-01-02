#!/bin/bash
# Script para configurar y ejecutar AppLab en Fedora Linux

echo "🔧 Configurando AppLab..."

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "🔌 Activando entorno virtual..."
source venv/bin/activate

# Instalar/actualizar dependencias
echo "📥 Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

# Crear carpeta uploads si no existe
if [ ! -d "uploads" ]; then
    mkdir uploads
    echo "📁 Carpeta uploads creada"
fi

# Ejecutar la aplicación
echo ""
echo "🚀 Iniciando AppLab..."
echo "📍 La aplicación estará disponible en: http://localhost:5000"
echo "⏹️  Para detener: Ctrl+C"
echo ""

cd backend
python app.py
