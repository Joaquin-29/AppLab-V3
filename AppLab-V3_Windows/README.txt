# AppLab-V3 - Sistema de Gestión de Inventario

Aplicación web para gestionar inventario, recetas y planificación de producción.

## 🚀 Instalación y Uso

### Para Usuarios (Windows)

1. **Descarga** el archivo `AppLab-V3.exe` desde el enlace proporcionado
2. **Extrae** el archivo ZIP en cualquier carpeta de tu PC
3. **Haz doble clic** en `AppLab-V3.exe`
4. **El navegador se abre automáticamente** en http://localhost:5000

**¡Eso es todo!** No necesitas instalar nada más.

### Características

- ✅ **Completamente standalone** - incluye Python y todas las dependencias
- ✅ **Base de datos persistente** - los datos se guardan automáticamente
- ✅ **Interfaz web moderna** - funciona en cualquier navegador
- ✅ **Sin instalación** - solo descargar y ejecutar

## 📊 Funcionalidades

- **📦 Gestión de Inventario**: Carga archivos XLS/CSV de stock
- **🍳 Gestión de Recetas**: Define composiciones de productos
- **🏭 Planificación de Producción**: Verifica si tienes suficientes materiales
- **📅 Control de Vencimientos**: Seguimiento de fechas de caducidad
- **🔄 Actualización Automática**: Actualiza stock existente

## 📁 Estructura de Archivos

### Para Inventario (XLS/CSV)
Debe contener columnas como:
- Artículo (código del producto)
- Nombre
- Lote
- Vencimiento (fecha)
- Unidad
- Cantidad

### Para Recetas (XLS/CSV)
Debe contener:
- Artículo (código de la receta)
- Componente (código del producto)
- Cantidad
- Unidad

## 🛠️ Para Desarrolladores

### Requisitos
- Python 3.8+
- pip

### Instalación
```bash
pip install -r requirements.txt
python backend/app.py
```

### Crear Ejecutable
```bash
./build_exe.sh
```

## 📍 Ubicación de Datos

Los datos se guardan en:
- **Windows**: `C:\Users\[Usuario]\AppLab-V3\`
- **Archivos subidos**: Se guardan en la carpeta `uploads`

## 🆘 Solución de Problemas

- **El EXE no funciona**: Asegúrate de extraer todo el ZIP
- **Puerto ocupado**: Cambia el puerto en la configuración
- **Datos no se guardan**: Verifica permisos de escritura

## 📧 Soporte

Para problemas o preguntas, contacta al desarrollador.