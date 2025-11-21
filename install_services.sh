#!/bin/bash
# Script para instalar los servicios systemd de RoboMesha
# Ejecutar con: sudo ./install_services.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SYSTEMD_DIR="$SCRIPT_DIR/systemd"
SERVICE_DIR="/etc/systemd/system"

echo "🔧 Instalando servicios systemd de RoboMesha..."
echo ""

# Verificar que estamos como root o con sudo
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Error: Este script debe ejecutarse con sudo"
    echo "   Ejecuta: sudo $0"
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

# Copiar archivos de servicio
echo "📋 Copiando archivos de servicio a $SERVICE_DIR..."
cp "$SYSTEMD_DIR/robomesha-backend.service" "$SERVICE_DIR/"
cp "$SYSTEMD_DIR/robomesha-frontend.service" "$SERVICE_DIR/"

# Actualizar las rutas en los servicios (ajustar al usuario real)
CURRENT_USER=${SUDO_USER:-$USER}
CURRENT_HOME=$(getent passwd "$CURRENT_USER" | cut -d: -f6)
if [ -z "$CURRENT_HOME" ] || [ "$CURRENT_HOME" = "/" ]; then
    CURRENT_HOME="/home/$CURRENT_USER"
fi

PROJECT_DIR="$CURRENT_HOME/New-interface"
BACKEND_VENV="$PROJECT_DIR/Backend/venv"

echo "🔧 Ajustando rutas para usuario: $CURRENT_USER"
echo "   Proyecto en: $PROJECT_DIR"
echo "   Venv en: $BACKEND_VENV"

# Reemplazar rutas en los servicios
sed -i "s|/home/admin|$CURRENT_HOME|g" "$SERVICE_DIR/robomesha-backend.service"
sed -i "s|/home/admin|$CURRENT_HOME|g" "$SERVICE_DIR/robomesha-frontend.service"
sed -i "s|User=admin|User=$CURRENT_USER|g" "$SERVICE_DIR/robomesha-backend.service"
sed -i "s|User=admin|User=$CURRENT_USER|g" "$SERVICE_DIR/robomesha-frontend.service"
sed -i "s|Group=admin|Group=$CURRENT_USER|g" "$SERVICE_DIR/robomesha-backend.service"
sed -i "s|Group=admin|Group=$CURRENT_USER|g" "$SERVICE_DIR/robomesha-frontend.service"

# Verificar que el venv existe
if [ ! -d "$BACKEND_VENV" ]; then
    echo "⚠️  Advertencia: No se encuentra el entorno virtual en $BACKEND_VENV"
    echo "   El servicio fallará hasta que crees el venv:"
    echo "   cd $PROJECT_DIR/Backend && python3 -m venv venv"
fi

# Verificar que node_modules existe
if [ ! -d "$PROJECT_DIR/Frontend/node_modules" ]; then
    echo "⚠️  Advertencia: No se encuentra node_modules en $PROJECT_DIR/Frontend"
    echo "   El servicio fallará hasta que instales las dependencias:"
    echo "   cd $PROJECT_DIR/Frontend && npm install"
fi

# Recargar systemd
echo ""
echo "🔄 Recargando systemd..."
systemctl daemon-reload

# Habilitar servicios para que inicien al arrancar
echo "✅ Habilitando servicios para inicio automático..."
systemctl enable robomesha-backend.service
systemctl enable robomesha-frontend.service

echo ""
echo "✅ Servicios instalados correctamente!"
echo ""
echo "📝 Comandos útiles:"
echo "   Iniciar servicios ahora:"
echo "     sudo systemctl start robomesha-backend"
echo "     sudo systemctl start robomesha-frontend"
echo ""
echo "   Ver estado:"
echo "     sudo systemctl status robomesha-backend"
echo "     sudo systemctl status robomesha-frontend"
echo ""
echo "   Ver logs:"
echo "     sudo journalctl -u robomesha-backend -f"
echo "     sudo journalctl -u robomesha-frontend -f"
echo ""
echo "   Detener servicios:"
echo "     sudo systemctl stop robomesha-backend"
echo "     sudo systemctl stop robomesha-frontend"
echo ""
echo "   Deshabilitar inicio automático:"
echo "     sudo systemctl disable robomesha-backend"
echo "     sudo systemctl disable robomesha-frontend"
echo ""
echo "🚀 Los servicios se iniciarán automáticamente al reiniciar la Raspberry Pi"

