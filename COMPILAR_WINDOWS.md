# Guía para compilar AppLab a .exe desde Linux

## Opción 1: GitHub Actions (Recomendado)

### Compilación automática con release
1. Hacé commit de tus cambios
2. Creá un tag con versión:
   ```bash
   git tag v1.0
   git push origin v1.0
   ```
3. GitHub Actions compilará automáticamente y creará un release con el .exe

### Compilación manual desde GitHub
1. Ve a tu repositorio en GitHub
2. Click en "Actions"
3. Selecciona "Build Windows EXE"
4. Click en "Run workflow"
5. Descarga el artefacto generado

## Opción 2: Wine + PyInstaller (Local en Linux)

### Instalación
```bash
# Instalar Wine
sudo apt install wine wine64 winetricks

# Configurar Wine
winecfg  # Primera vez, espera que se configure

# Instalar Python en Wine
wget https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe
wine python-3.11.7-amd64.exe /quiet InstallAllUsers=1 PrependPath=1

# Instalar dependencias
wine python -m pip install -r requirements.txt
wine python -m pip install pyinstaller
```

### Compilar
```bash
wine pyinstaller AppLab.spec
```

El .exe estará en `dist/AppLab.exe`

## Opción 3: Docker (Más confiable que Wine)

### Crear Dockerfile para compilación
```bash
# Crear archivo compile_windows.sh
cat > compile_windows.sh << 'EOF'
#!/bin/bash
docker run --rm -v "$(pwd):/src" cdrx/pyinstaller-windows \
  "pip install -r requirements.txt && pyinstaller AppLab.spec"
EOF

chmod +x compile_windows.sh
./compile_windows.sh
```

## Recomendación

**Usa GitHub Actions** (Opción 1). Es la forma más confiable:
- No necesitas instalar nada extra en tu sistema
- Siempre compila en un ambiente limpio de Windows
- Crea releases automáticos
- Guarda histórico de compilaciones
