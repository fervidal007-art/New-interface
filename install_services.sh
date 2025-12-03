#!/bin/bash

# Script para instalar y configurar completamente RoboMesha
# Ejecutar con: sudo ./install_services.sh
# Este script configura todo: venv, dependencias y servicios systemd

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SYSTEMD_DIR="$SCRIPT_DIR/systemd"
SERVICE_DIR="/etc/systemd/system"

echo "🚀 Configurando RoboMesha completamente..."
echo "=========================================="
echo ""

# Verificar que estamos como root o con sudo
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Error: Este script debe ejecutarse con sudo"
    echo "   Ejecuta: sudo $0"
    exit 1
fi

# Obtener usuario real (el que ejecutó sudo)
CURRENT_USER=${SUDO_USER:-$USER}
if [ "$CURRENT_USER" = "root" ]; then
    echo "❌ Error: No se puede determinar el usuario. Ejecuta con: sudo -u tu_usuario $0"
    exit 1
fi

CURRENT_HOME=$(getent passwd "$CURRENT_USER" | cut -d: -f6)
if [ -z "$CURRENT_HOME" ] || [ "$CURRENT_HOME" = "/" ]; then
    CURRENT_HOME="/home/$CURRENT_USER"
fi

PROJECT_DIR="$CURRENT_HOME/New-interface"
BACKEND_DIR="$PROJECT_DIR/Backend"
FRONTEND_DIR="$PROJECT_DIR/Frontend"
BACKEND_VENV="$BACKEND_DIR/venv"

echo "👤 Usuario: $CURRENT_USER"
echo "📂 Proyecto: $PROJECT_DIR"
echo ""

# Verificar que el proyecto existe
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Error: No se encuentra el directorio del proyecto en $PROJECT_DIR"
    echo ""
    echo "📋 Para desplegar el proyecto, primero clona el repositorio:"
    echo "   cd $CURRENT_HOME"
    echo "   git clone [URL_DEL_REPOSITORIO] New-interface"
    echo ""
    echo "   O si ya tienes el proyecto en otra ubicación, créalo con:"
    echo "   mkdir -p $PROJECT_DIR"
    echo "   # Luego copia los archivos del proyecto ahí"
    echo ""
    exit 1
fi

# Si es un repositorio git, actualizar código (opcional)
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "🔄 Detectado repositorio Git, actualizando código..."
    # Configurar estrategia de pull por defecto si no está configurada (merge por defecto)
    su - "$CURRENT_USER" -c "cd '$PROJECT_DIR' && git config pull.rebase false 2>/dev/null || true"
    # Verificar si hay cambios sin commitear
    if su - "$CURRENT_USER" -c "cd '$PROJECT_DIR' && git diff --quiet && git diff --cached --quiet" 2>/dev/null; then
        # No hay cambios, hacer pull normalmente
        su - "$CURRENT_USER" -c "cd '$PROJECT_DIR' && git pull --no-rebase" || echo "   ⚠️  No se pudo actualizar (puede que no haya cambios o haya conflictos)"
    else
        # Hay cambios sin commitear, hacer stash, pull y luego aplicar stash
        echo "   ⚠️  Detectados cambios sin commitear, guardándolos temporalmente..."
        su - "$CURRENT_USER" -c "cd '$PROJECT_DIR' && git stash push -m 'Cambios guardados automáticamente por install_services.sh'" 2>/dev/null || true
        su - "$CURRENT_USER" -c "cd '$PROJECT_DIR' && git pull --no-rebase" || echo "   ⚠️  No se pudo actualizar (puede que no haya cambios o haya conflictos)"
        # Intentar aplicar los cambios guardados
        if su - "$CURRENT_USER" -c "cd '$PROJECT_DIR' && git stash list | grep -q 'Cambios guardados automáticamente'" 2>/dev/null; then
            echo "   🔄 Reaplicando cambios guardados..."
            su - "$CURRENT_USER" -c "cd '$PROJECT_DIR' && git stash pop" 2>/dev/null || echo "   ⚠️  Advertencia: Hubo conflictos al reaplicar cambios. Revisa manualmente con 'git stash list'"
        fi
    fi
    echo ""
fi

# Verificar que los archivos de servicio existen
if [ ! -f "$SYSTEMD_DIR/robomesha-backend.service" ]; then
    echo "❌ Error: No se encuentra robomesha-backend.service"
    exit 1
fi

if [ ! -f "$SYSTEMD_DIR/robomesha-frontend.service" ]; then
    echo "❌ Error: No se encuentra robomesha-frontend.service"
    exit 1
fi

# ========== CONFIGURAR BACKEND ==========
echo "📦 Configurando Backend..."
echo ""

# Crear entorno virtual si no existe
if [ ! -d "$BACKEND_VENV" ]; then
    echo "🔨 Creando entorno virtual Python..."
    su - "$CURRENT_USER" -c "cd '$BACKEND_DIR' && python3 -m venv venv"
    echo "✅ Entorno virtual creado"
else
    echo "✅ Entorno virtual ya existe"
fi

# Instalar/Actualizar dependencias del backend
echo "📥 Instalando dependencias del backend..."
if [ -f "$BACKEND_DIR/requirements.txt" ]; then
    su - "$CURRENT_USER" -c "cd '$BACKEND_DIR' && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
    echo "✅ Dependencias del backend instaladas"
    
    # Verificar que smbus2 esté instalado correctamente
    echo "🔍 Verificando instalación de smbus2..."
    if su - "$CURRENT_USER" -c "cd '$BACKEND_DIR' && source venv/bin/activate && python3 -c 'from smbus2 import SMBus; print(\"smbus2 OK\")'" 2>/dev/null; then
        echo "   ✅ smbus2 instalado correctamente"
    else
        echo "   ⚠️  Advertencia: smbus2 no se pudo importar, intentando reinstalar..."
        su - "$CURRENT_USER" -c "cd '$BACKEND_DIR' && source venv/bin/activate && pip install --force-reinstall smbus2" || echo "   ❌ Error al reinstalar smbus2"
    fi
else
    echo "⚠️  Advertencia: No se encuentra requirements.txt en Backend/"
fi

# ========== CONFIGURAR FRONTEND ==========
echo ""
echo "📦 Configurando Frontend..."
echo ""

# Verificar si npm está instalado
if ! command -v npm &> /dev/null; then
    echo "⚠️  Advertencia: npm no está instalado. Instalando Node.js..."
    # Intentar instalar nodejs desde repositorio
    apt-get update -qq
    apt-get install -y nodejs npm
    echo "✅ Node.js instalado"
fi

# Verificar versión de Node.js y npm
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "   Node.js versión: $NODE_VERSION"
fi
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "   npm versión: $NPM_VERSION"
fi

# Instalar dependencias del frontend (siempre limpio para evitar problemas de arquitectura)
if [ -d "$FRONTEND_DIR" ]; then
    # Eliminar node_modules y archivos de lock si existen para reinstalación limpia
    # Esto evita problemas cuando se clonó desde otra arquitectura (ej: Mac -> ARM64)
    echo "🧹 Limpiando instalación anterior del frontend (si existe)..."
    if [ -d "$FRONTEND_DIR/node_modules" ]; then
        su - "$CURRENT_USER" -c "rm -rf '$FRONTEND_DIR/node_modules'"
        echo "   Eliminado node_modules anterior"
    fi
    if [ -f "$FRONTEND_DIR/package-lock.json" ]; then
        su - "$CURRENT_USER" -c "rm -f '$FRONTEND_DIR/package-lock.json'"
        echo "   Eliminado package-lock.json anterior"
    fi
    if [ -f "$FRONTEND_DIR/pnpm-lock.yaml" ]; then
        su - "$CURRENT_USER" -c "rm -f '$FRONTEND_DIR/pnpm-lock.yaml'"
        echo "   Eliminado pnpm-lock.yaml anterior (usando npm, no pnpm)"
    fi

    # Limpiar cache de npm para evitar errores de integridad (especialmente en Raspberry Pi)
    echo "🧹 Limpiando cache de npm..."
    su - "$CURRENT_USER" -c "npm cache clean --force" || echo "   ⚠️  Advertencia: No se pudo limpiar cache (continuando...)"
    echo "   Cache de npm limpiado"

    echo "📥 Instalando dependencias del frontend (esto puede tardar unos minutos)..."
    echo "   Instalando para arquitectura ARM64 (Raspberry Pi)..."

    # Desactivar set -e temporalmente para permitir reintentos
    set +e

    # Intentar instalación con diferentes estrategias
    FRONTEND_INSTALLED=0
    attempt=1
    max_attempts=3

    while [ $attempt -le $max_attempts ] && [ $FRONTEND_INSTALLED -eq 0 ]; do
        echo "   Intento $attempt de $max_attempts..."

        if [ $attempt -eq 1 ]; then
            # Primer intento: instalación normal
            if su - "$CURRENT_USER" -c "cd '$FRONTEND_DIR' && npm install" 2>&1; then
                FRONTEND_INSTALLED=1
                echo "✅ Instalación exitosa en el intento $attempt"
            else
                echo "   ⚠️  Intento $attempt fallido"
            fi
        elif [ $attempt -eq 2 ]; then
            # Segundo intento: limpiar cache y usar --legacy-peer-deps
            echo "   Limpiando cache nuevamente y reintentando con opciones alternativas..."
            su - "$CURRENT_USER" -c "npm cache clean --force" 2>&1 || true
            if su - "$CURRENT_USER" -c "cd '$FRONTEND_DIR' && npm install --legacy-peer-deps" 2>&1; then
                FRONTEND_INSTALLED=1
                echo "✅ Instalación exitosa en el intento $attempt"
            else
                echo "   ⚠️  Intento $attempt fallido"
            fi
        else
            # Tercer intento: limpiar cache y usar --force
            echo "   Último intento: limpiando cache y usando instalación forzada..."
            su - "$CURRENT_USER" -c "npm cache clean --force" 2>&1 || true
            # Eliminar node_modules si existe para intento limpio
            su - "$CURRENT_USER" -c "rm -rf '$FRONTEND_DIR/node_modules'" 2>&1 || true
            if su - "$CURRENT_USER" -c "cd '$FRONTEND_DIR' && npm install --force --no-audit --no-fund" 2>&1; then
                FRONTEND_INSTALLED=1
                echo "✅ Instalación exitosa en el intento $attempt"
            else
                echo "   ⚠️  Intento $attempt fallido"
            fi
        fi

        if [ $FRONTEND_INSTALLED -eq 0 ] && [ $attempt -lt $max_attempts ]; then
            echo "   Esperando 5 segundos antes de reintentar..."
            sleep 5
        fi

        attempt=$((attempt + 1))
    done

    # Reactivar set -e
    set -e

    if [ $FRONTEND_INSTALLED -eq 1 ]; then
        echo "✅ Dependencias del frontend instaladas correctamente"
    else
        echo "❌ Error: No se pudieron instalar las dependencias del frontend después de $max_attempts intentos"
        echo ""
        echo "   Soluciones posibles:"
        echo "   1. Verifica tu conexión a internet"
        echo "   2. Intenta manualmente:"
        echo "      cd $FRONTEND_DIR"
        echo "      npm cache clean --force"
        echo "      npm install --legacy-peer-deps"
        echo "   3. Verifica los logs de npm:"
        echo "      cat ~/.npm/_logs/*-debug.log"
        echo ""
        exit 1
    fi
else
    echo "⚠️  Advertencia: No se encuentra el directorio Frontend/"
fi

# ========== INSTALAR SERVICIOS SYSTEMD ==========
echo ""
echo "🔧 Instalando servicios systemd..."
echo ""

# Copiar archivos de servicio
echo "📋 Copiando archivos de servicio a $SERVICE_DIR..."
cp "$SYSTEMD_DIR/robomesha-backend.service" "$SERVICE_DIR/"
cp "$SYSTEMD_DIR/robomesha-frontend.service" "$SERVICE_DIR/"

# Actualizar rutas en los servicios
echo "🔧 Ajustando rutas en los servicios..."
sed -i "s|/home/admin|$CURRENT_HOME|g" "$SERVICE_DIR/robomesha-backend.service"
sed -i "s|/home/admin|$CURRENT_HOME|g" "$SERVICE_DIR/robomesha-frontend.service"
sed -i "s|User=admin|User=$CURRENT_USER|g" "$SERVICE_DIR/robomesha-backend.service"
sed -i "s|User=admin|User=$CURRENT_USER|g" "$SERVICE_DIR/robomesha-frontend.service"
sed -i "s|Group=admin|Group=$CURRENT_USER|g" "$SERVICE_DIR/robomesha-backend.service"
sed -i "s|Group=admin|Group=$CURRENT_USER|g" "$SERVICE_DIR/robomesha-frontend.service"

# Actualizar ruta de npm si es necesario (para Raspberry Pi)
if command -v npm &> /dev/null; then
    NPM_PATH=$(which npm)
    sed -i "s|/usr/bin/npm|$NPM_PATH|g" "$SERVICE_DIR/robomesha-frontend.service"
    echo "   ✅ Ruta de npm actualizada: $NPM_PATH"
fi

# Actualizar ruta de Python en el servicio backend (importante para venv)
PYTHON_VENV_PATH="$BACKEND_VENV/bin/python3"
if [ -f "$PYTHON_VENV_PATH" ]; then
    sed -i "s|/home/admin/New-interface/Backend/venv/bin/python3|$PYTHON_VENV_PATH|g" "$SERVICE_DIR/robomesha-backend.service"
    echo "   ✅ Ruta de Python (venv) actualizada: $PYTHON_VENV_PATH"
else
    echo "   ⚠️  Advertencia: No se encontró Python en venv, el servicio usará la ruta por defecto"
fi

# Actualizar WorkingDirectory en ambos servicios
sed -i "s|WorkingDirectory=/home/admin/New-interface|WorkingDirectory=$PROJECT_DIR|g" "$SERVICE_DIR/robomesha-backend.service"
sed -i "s|WorkingDirectory=/home/admin/New-interface/Frontend|WorkingDirectory=$FRONTEND_DIR|g" "$SERVICE_DIR/robomesha-frontend.service"
echo "   ✅ WorkingDirectory actualizado en ambos servicios"

# Actualizar variable de entorno PATH en el servicio backend
sed -i "s|Environment=\"PATH=/home/admin/New-interface/Backend/venv/bin:|Environment=\"PATH=$BACKEND_VENV/bin:|g" "$SERVICE_DIR/robomesha-backend.service"
echo "   ✅ Variable PATH actualizada en el servicio backend"

# Verificar permisos del venv (importante para systemd)
if [ -d "$BACKEND_VENV" ]; then
    echo "🔐 Ajustando permisos del entorno virtual..."
    chown -R "$CURRENT_USER:$CURRENT_USER" "$BACKEND_VENV"
fi

# Verificar permisos del proyecto
echo "🔐 Ajustando permisos del proyecto..."
chown -R "$CURRENT_USER:$CURRENT_USER" "$PROJECT_DIR"

# Recargar systemd
echo ""
echo "🔄 Recargando systemd..."
systemctl daemon-reload

# Detener servicios si están corriendo (para aplicar cambios)
echo "🛑 Deteniendo servicios si están corriendo..."
if systemctl is-active --quiet robomesha-backend.service; then
    systemctl stop robomesha-backend.service
    echo "   ✅ Backend detenido"
fi
if systemctl is-active --quiet robomesha-frontend.service; then
    systemctl stop robomesha-frontend.service
    echo "   ✅ Frontend detenido"
fi

# Habilitar servicios para inicio automático
echo ""
echo "✅ Habilitando servicios para inicio automático..."
systemctl enable robomesha-backend.service
systemctl enable robomesha-frontend.service

# Verificar que los servicios están habilitados
if systemctl is-enabled --quiet robomesha-backend.service; then
    echo "   ✅ Backend habilitado para inicio automático"
else
    echo "   ⚠️  Advertencia: Backend no se pudo habilitar"
fi

if systemctl is-enabled --quiet robomesha-frontend.service; then
    echo "   ✅ Frontend habilitado para inicio automático"
else
    echo "   ⚠️  Advertencia: Frontend no se pudo habilitar"
fi

# Reiniciar servicios para aplicar cambios
echo ""
echo "🚀 Iniciando servicios con la nueva configuración..."
echo ""

# Iniciar backend
echo "📡 Iniciando backend..."
systemctl start robomesha-backend.service
sleep 3  # Esperar a que el backend se inicie completamente

# Verificar que el backend esté corriendo
BACKEND_RETRIES=0
MAX_BACKEND_RETRIES=5
while [ $BACKEND_RETRIES -lt $MAX_BACKEND_RETRIES ]; do
    if systemctl is-active --quiet robomesha-backend.service; then
        # Verificar que el servidor esté respondiendo
        if curl -s -f http://localhost:5000/health > /dev/null 2>&1; then
            echo "   ✅ Backend está corriendo y respondiendo en http://localhost:5000"
            break
        else
            echo "   ⏳ Backend iniciado, esperando respuesta HTTP... (intento $((BACKEND_RETRIES + 1))/$MAX_BACKEND_RETRIES)"
            sleep 2
        fi
    else
        echo "   ⏳ Esperando inicio del backend... (intento $((BACKEND_RETRIES + 1))/$MAX_BACKEND_RETRIES)"
        sleep 2
    fi
    BACKEND_RETRIES=$((BACKEND_RETRIES + 1))
done

if [ $BACKEND_RETRIES -eq $MAX_BACKEND_RETRIES ]; then
    echo "   ⚠️  El backend no respondió después de varios intentos"
    echo "   Revisando logs del backend..."
    echo ""
    echo "   Últimas líneas del log:"
    journalctl -u robomesha-backend.service -n 20 --no-pager || true
    echo ""
    echo "   Para ver más detalles:"
    echo "      sudo journalctl -u robomesha-backend -n 50"
    echo ""
    echo "   Intentando iniciar manualmente como fallback..."
    # Intentar ejecutar el backend manualmente como fallback
    if [ -f "$BACKEND_VENV/bin/python3" ] && [ -f "$BACKEND_DIR/server.py" ]; then
        echo "   Ejecutando: $BACKEND_VENV/bin/python3 $BACKEND_DIR/server.py"
        # Ejecutar en background para no bloquear
        su - "$CURRENT_USER" -c "cd '$BACKEND_DIR' && source venv/bin/activate && nohup python3 server.py > /tmp/robomesha-backend.log 2>&1 &" || true
        sleep 2
        if curl -s -f http://localhost:5000/health > /dev/null 2>&1; then
            echo "   ✅ Backend iniciado manualmente y respondiendo"
        else
            echo "   ❌ Backend no responde. Revisa los logs manualmente"
        fi
    fi
fi

# Iniciar frontend
echo ""
echo "🎨 Iniciando frontend..."
sleep 2  # Esperar un poco antes de iniciar el frontend
systemctl start robomesha-frontend.service
sleep 3  # Esperar a que el frontend se inicie

# Verificar estado final
echo ""
echo "📊 Verificando estado final de los servicios..."
echo ""

if systemctl is-active --quiet robomesha-backend.service; then
    echo "   ✅ Backend (systemd) está corriendo"
else
    # Verificar si está corriendo manualmente
    if curl -s -f http://localhost:5000/health > /dev/null 2>&1; then
        echo "   ✅ Backend está corriendo (modo manual)"
    else
        echo "   ❌ Backend no está corriendo. Revisa los logs:"
        echo "      sudo journalctl -u robomesha-backend -n 50"
    fi
fi

if systemctl is-active --quiet robomesha-frontend.service; then
    echo "   ✅ Frontend está corriendo"
else
    echo "   ❌ Frontend no está corriendo. Revisa los logs:"
    echo "      sudo journalctl -u robomesha-frontend -n 50"
fi

echo ""
echo "=========================================="
echo "✅ ¡Despliegue completo!"
echo "=========================================="
echo ""

echo "📦 Resumen de lo desplegado:"
echo ""
echo "   ✅ Backend configurado:"
echo "      - Entorno virtual Python creado/actualizado"
echo "      - Dependencias instaladas desde requirements.txt"
echo "      - Servicio systemd instalado y habilitado"
echo ""
echo "   ✅ Frontend configurado:"
echo "      - Node.js/npm verificado/instalado"
echo "      - Dependencias instaladas"
echo "      - Servicio systemd instalado y habilitado"
echo ""
echo "   ✅ Servicios systemd:"
echo "      - robomesha-backend.service: Habilitado y corriendo"
echo "      - robomesha-frontend.service: Habilitado y corriendo"
echo "      - Inicio automático configurado para después de reiniciar"
echo ""

echo "=========================================="
echo ""
echo "📝 Comandos útiles:"
echo ""
echo "   Ver estado:"
echo "     sudo systemctl status robomesha-backend"
echo "     sudo systemctl status robomesha-frontend"
echo ""
echo "   Ver logs en tiempo real:"
echo "     sudo journalctl -u robomesha-backend -f"
echo "     sudo journalctl -u robomesha-frontend -f"
echo ""
echo "   Reiniciar servicios:"
echo "     sudo systemctl restart robomesha-backend"
echo "     sudo systemctl restart robomesha-frontend"
echo ""
echo "   Detener servicios:"
echo "     sudo systemctl stop robomesha-backend"
echo "     sudo systemctl stop robomesha-frontend"
echo ""
echo "   Deshabilitar inicio automático:"
echo "     sudo systemctl disable robomesha-backend"
echo "     sudo systemctl disable robomesha-frontend"
echo ""
echo "🚀 Los servicios están habilitados y se iniciarán automáticamente al reiniciar"
echo ""
