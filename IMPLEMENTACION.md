# AppLab - Sistema de Gestión de Inventario y Producción

## Resumen de Implementación

### 1. Script de Procesamiento de Inventario
**Archivo:** `backend/utils/process_inventario_csv.py`

Este script procesa archivos CSV de inventario y carga los productos en la base de datos:

- **Limpia filas innecesarias** del CSV (encabezados, metadatos)
- **Normaliza unidades de medida** (Kg → g, mL → L)
- **Procesa fechas de vencimiento**
- **Maneja lotes de productos**
- **Actualiza o crea productos** según si ya existen

### 2. Modelos de Base de Datos

#### Producto (`backend/models/producto.py`)
- `codigo`: Código del producto
- `nombre`: Nombre del producto
- `lote`: Número de lote
- `unidad`: Unidad de medida normalizada (g, L, uni)
- `cantidad_disponible`: Cantidad en stock (Float)
- `fecha_vencimiento`: Fecha de vencimiento del lote

#### Receta (`backend/models/receta.py`)
- `codigo`: Código de la receta
- `nombre`: Nombre de la receta
- Relación con componentes

#### RecetaComponente (`backend/models/receta_componente.py`)
- `receta_id`: ID de la receta
- `producto_id`: ID del producto necesario
- `cantidad_necesaria`: Cantidad del producto necesaria
- `unidad`: Unidad de medida

### 3. Rutas y Páginas

#### Página Principal (`/`)
- Dashboard con enlaces a todas las funcionalidades
- Descripción de características del sistema

#### Página de Carga (`/cargar`)
- Formulario para subir archivos de stock (XLS, XLSX, CSV)
- Formulario para subir archivos de recetas
- Información sobre formatos esperados

#### Página de Stock (`/stock`)
- Tabla con todos los productos del inventario
- Búsqueda en tiempo real
- Información de lote, cantidad, unidad y vencimiento
- Indicadores visuales de estado

#### Página de Recetas (`/recetas`)
- Cards con todas las recetas
- Muestra componentes de cada receta
- Búsqueda en tiempo real

#### Página de Producción (`/produccion`)
- **Selección múltiple de recetas** con checkboxes
- **Campo de cantidad** para cada receta seleccionada
- **Cálculo inteligente** que verifica:
  - Si hay suficiente stock para producir
  - Qué lotes se usarán (priorizando por fecha de vencimiento)
  - Qué productos faltan y en qué cantidad
- **Modal de resultados** con tabla detallada

### 4. Funcionalidades Implementadas

✅ **Importación de archivos**
- Sube archivos XLS, XLSX o CSV
- Procesamiento automático según tipo (stock o recetas)
- Conversión de unidades automática

✅ **Gestión de Stock**
- Visualización completa del inventario
- Seguimiento de lotes y vencimientos
- Búsqueda y filtrado

✅ **Gestión de Recetas**
- Visualización de recetas y componentes
- Relación con productos del inventario

✅ **Cálculo de Producción**
- Selección múltiple de recetas
- Configuración de cantidades a producir
- Algoritmo FIFO (First In, First Out) basado en vencimientos
- Verificación de disponibilidad de stock
- Reporte detallado de productos a usar

### 5. Características Técnicas

- **Framework:** Flask con SQLAlchemy
- **Frontend:** Bootstrap 5.3.8 con Bootstrap Icons
- **Base de datos:** SQLite
- **Procesamiento de datos:** Pandas
- **Interfaz:** Responsive y moderna

### 6. Próximos Pasos Sugeridos

1. **Validación de la carga de archivos**
   - Probar con archivos reales
   - Ajustar parseo según formato exacto

2. **Migraciones de base de datos**
   - Configurar Flask-Migrate para gestionar cambios en modelos

3. **Mejoras en el cálculo de producción**
   - Considerar productos con múltiples lotes
   - Optimizar el algoritmo FIFO
   - Agregar alertas de vencimiento próximo

4. **Reportes**
   - Exportar resultados a PDF o Excel
   - Historial de producciones

5. **Autenticación**
   - Sistema de usuarios y permisos
   - Roles (administrador, operador, etc.)

## Cómo Usar

### 1. Cargar Stock
1. Ir a "Cargar Archivos"
2. Seleccionar archivo de inventario (CSV o Excel)
3. Hacer clic en "Cargar Stock"

### 2. Cargar Recetas
1. Ir a "Cargar Archivos"
2. Seleccionar archivo de recetas (CSV con formato esperado)
3. Hacer clic en "Cargar Recetas"

### 3. Calcular Producción
1. Ir a "Producción"
2. Marcar las recetas que deseas producir
3. Ajustar la cantidad para cada receta
4. Hacer clic en "Calcular Producción"
5. Ver los resultados en el modal

## Estructura del Proyecto

```
AppLab-V3/
├── backend/
│   ├── app.py                      # Aplicación Flask principal
│   ├── models/
│   │   ├── producto.py             # Modelo Producto
│   │   ├── receta.py               # Modelo Receta
│   │   └── receta_componente.py    # Modelo RecetaComponente
│   ├── templates/
│   │   ├── base.html               # Template base
│   │   ├── index.html              # Página principal
│   │   ├── cargar.html             # Página de carga
│   │   ├── stock.html              # Página de stock
│   │   ├── recetas.html            # Página de recetas
│   │   └── produccion.html         # Página de producción
│   └── utils/
│       ├── process_inventario_csv.py   # Procesador de inventario
│       └── process_recipes_csv.py      # Procesador de recetas
└── uploads/                        # Archivos subidos
```
