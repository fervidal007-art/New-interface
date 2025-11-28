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
    su - "$CURRENT_USER" -c "cd '$PROJECT_DIR' && git pull" || echo "   ⚠️  No se pudo actualizar (puede que no haya cambios o haya conflictos)"
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

# Instalar dependencias del frontend (siempre limpio para evitar problemas de arquitectura)
if [ -d "$FRONTEND_DIR" ]; then
    # Eliminar node_modules y package-lock.json si existen para reinstalación limpia
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
    
    echo "📥 Instalando dependencias del frontend (esto puede tardar unos minutos)..."
    echo "   Instalando para arquitectura ARM64 (Raspberry Pi)..."
    su - "$CURRENT_USER" -c "cd '$FRONTEND_DIR' && npm install"
    echo "✅ Dependencias del frontend instaladas correctamente"
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
echo "🚀 Reiniciando servicios con la nueva configuración..."
systemctl start robomesha-backend.service
sleep 2  # Esperar un poco antes de iniciar el frontend
systemctl start robomesha-frontend.service

# Esperar un momento y verificar estado
sleep 3
echo ""
echo "📊 Verificando estado de los servicios..."
echo ""

if systemctl is-active --quiet robomesha-backend.service; then
    echo "   ✅ Backend está corriendo"
else
    echo "   ❌ Backend no está corriendo. Revisa los logs:"
    echo "      sudo journalctl -u robomesha-backend -n 50"
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
