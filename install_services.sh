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
    echo "   Asegúrate de haber clonado/creado el proyecto en esa ubicación"
    exit 1
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

# Instalar dependencias del frontend
if [ -d "$FRONTEND_DIR" ]; then
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        echo "📥 Instalando dependencias del frontend (esto puede tardar)..."
        su - "$CURRENT_USER" -c "cd '$FRONTEND_DIR' && npm install"
        echo "✅ Dependencias del frontend instaladas"
    else
        echo "✅ node_modules ya existe, saltando instalación"
        echo "   (Si necesitas reinstalar: cd '$FRONTEND_DIR' && npm install)"
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

# Habilitar servicios para inicio automático
echo "✅ Habilitando servicios para inicio automático..."
systemctl enable robomesha-backend.service
systemctl enable robomesha-frontend.service

echo ""
echo "=========================================="
echo "✅ ¡Configuración completa!"
echo "=========================================="
echo ""
echo "📝 Comandos útiles:"
echo ""
echo "   Iniciar servicios ahora:"
echo "     sudo systemctl start robomesha-backend"
echo "     sudo systemctl start robomesha-frontend"
echo ""
echo "   Ver estado:"
echo "     sudo systemctl status robomesha-backend"
echo "     sudo systemctl status robomesha-frontend"
echo ""
echo "   Ver logs en tiempo real:"
echo "     sudo journalctl -u robomesha-backend -f"
echo "     sudo journalctl -u robomesha-frontend -f"
echo ""
echo "   Detener servicios:"
echo "     sudo systemctl stop robomesha-backend"
echo "     sudo systemctl stop robomesha-frontend"
echo ""
echo "   Reiniciar servicios:"
echo "     sudo systemctl restart robomesha-backend"
echo "     sudo systemctl restart robomesha-frontend"
echo ""
echo "   Deshabilitar inicio automático:"
echo "     sudo systemctl disable robomesha-backend"
echo "     sudo systemctl disable robomesha-frontend"
echo ""
echo "🚀 Los servicios se iniciarán automáticamente al reiniciar la Raspberry Pi"
echo ""
