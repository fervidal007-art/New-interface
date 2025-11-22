#!/bin/bash
# Script para arreglar problemas de dependencias del frontend
# Útil cuando node_modules fue instalado en otra arquitectura

cd "$(dirname "$0")/Frontend"

echo "🧹 Limpiando instalación anterior del frontend..."
echo ""

# Eliminar node_modules y package-lock.json
if [ -d "node_modules" ]; then
    echo "   Eliminando node_modules..."
    rm -rf node_modules
fi

if [ -f "package-lock.json" ]; then
    echo "   Eliminando package-lock.json..."
    rm -f package-lock.json
fi

echo ""
echo "📥 Reinstalando dependencias para Raspberry Pi (ARM64)..."
echo "   Esto puede tardar unos minutos..."
echo ""

npm install

echo ""
echo "✅ ¡Listo! Las dependencias han sido reinstaladas correctamente."
echo "   Ahora puedes ejecutar: ./run_frontend.sh"

