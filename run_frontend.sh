#!/bin/bash
# Script para ejecutar el frontend en Raspberry Pi 5

cd "$(dirname "$0")/Frontend"

echo "🎨 Iniciando Frontend RoboMesha..."
echo "📂 Directorio: $(pwd)"
echo ""

# Verificar si node_modules existe
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependencias..."
    npm install
fi

# Ejecutar servidor de desarrollo
echo ""
echo "🌐 Iniciando servidor de desarrollo en http://localhost:5173"
echo "Presiona Ctrl+C para detener"
echo ""
npm run dev

