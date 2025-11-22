#!/bin/bash
# Script para arreglar problemas de dependencias del frontend
# Útil cuando node_modules fue instalado en otra arquitectura

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FRONTEND_DIR="$SCRIPT_DIR/Frontend"

# Verificar que el directorio Frontend existe
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Error: No se encuentra el directorio Frontend/"
    exit 1
fi

cd "$FRONTEND_DIR"

# Verificar permisos de escritura
if [ ! -w "." ]; then
    echo "⚠️  Advertencia: No tienes permisos de escritura en $FRONTEND_DIR"
    echo "   Verifica los permisos del directorio"
    exit 1
fi

echo "🧹 Limpiando instalación anterior del frontend..."
echo ""

# Eliminar node_modules y package-lock.json
if [ -d "node_modules" ]; then
    echo "   Eliminando node_modules..."
    rm -rf node_modules
    echo "   ✅ node_modules eliminado"
fi

if [ -f "package-lock.json" ]; then
    echo "   Eliminando package-lock.json..."
    rm -f package-lock.json
    echo "   ✅ package-lock.json eliminado"
fi

echo ""
echo "📥 Reinstalando dependencias para Raspberry Pi (ARM64)..."
echo "   Esto puede tardar unos minutos..."
echo ""

# Verificar que npm está disponible
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm no está instalado"
    echo "   Instala Node.js y npm primero"
    exit 1
fi

npm install

echo ""
echo "✅ ¡Listo! Las dependencias han sido reinstaladas correctamente."
echo "   Ahora puedes ejecutar: cd ~/New-interface && ./run_frontend.sh"

