#!/bin/bash
# Script para ejecutar el backend en Raspberry Pi 5

cd "$(dirname "$0")/Backend"

echo "🚀 Iniciando Backend RoboMesha..."
echo "📂 Directorio: $(pwd)"
echo ""

# Activar entorno virtual si existe, si no, usar Python del sistema
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Entorno virtual activado"
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
    echo "✅ Entorno virtual activado"
else
    echo "⚠️  No se encontró entorno virtual, usando Python del sistema"
fi

# Instalar/Actualizar dependencias
echo "📦 Verificando e instalando dependencias..."
pip3 install -r requirements.txt --quiet

# Ejecutar servidor
echo ""
echo "🌐 Iniciando servidor en http://localhost:5000"
echo "Presiona Ctrl+C para detener"
echo ""
python3 server.py

