# Sistema de Control RoboMesha

Sistema completo para controlar la mesa robótica RoboMesha mediante interfaz web. El sistema consta de un frontend React y un backend Python que comunica con los motores mediante I2C (simulado o real).

## 🏗️ Arquitectura

```
Frontend (React + Vite)  ←→  Backend (FastAPI + Socket.IO)  ←→  Motores I2C
    localhost:5173                   localhost:5000                  (Raspberry Pi)
```

## 📋 Requisitos

### Backend
- Python 3.11 o superior
- pip3
- (Opcional) smbus2 para I2C real en Raspberry Pi

### Frontend
- Node.js 18 o superior
- npm 7 o superior

## 🚀 Instalación Rápida

### 1. Clonar y preparar el proyecto

```bash
cd /Users/vidal/Documents/Personal/New-interface
```

### 2. Configurar Backend

```bash
cd Backend

# Crear entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate  # En Raspberry Pi

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Frontend

```bash
cd ../Frontend

# Instalar dependencias
npm install
```

## 🎮 Ejecución

En una Raspberry Pi 5, tienes tres opciones para ejecutar el sistema:

### Opción 1: Inicio Automático al Arrancar (Recomendado para Producción) 🚀

Para que el backend y frontend se inicien automáticamente cuando la Raspberry Pi arranca:

```bash
cd ~/New-interface
sudo ./install_services.sh
```

Este script:
- Instala servicios systemd (`robomesha-backend.service` y `robomesha-frontend.service`)
- Los habilita para iniciar automáticamente al arrancar
- Ajusta las rutas automáticamente según tu usuario

**Comandos útiles:**
```bash
# Ver estado de los servicios
sudo systemctl status robomesha-backend
sudo systemctl status robomesha-frontend

# Ver logs en tiempo real
sudo journalctl -u robomesha-backend -f
sudo journalctl -u robomesha-frontend -f

# Iniciar manualmente
sudo systemctl start robomesha-backend
sudo systemctl start robomesha-frontend

# Detener
sudo systemctl stop robomesha-backend
sudo systemctl stop robomesha-frontend
```

### Opción 2: Script Manual con tmux (Para Desarrollo)

```bash
cd ~/New-interface
./run_all.sh
```

Este script:
- Configura/activa el AP `ROBOMESHA` con SSID `ROBOMESHA` y clave `123456789`.
- Crea una sesión tmux `robomesha` con dos ventanas (`run_backend.sh` y `run_frontend.sh`).
- Se adjunta automáticamente a tmux (usa `Ctrl+B` seguido de `D` para salir y dejar todo corriendo).


### Terminal 1 - Backend

```bash
cd /Users/vidal/Documents/Personal/New-interface
./run_backend.sh
```

O manualmente:
```bash
cd Backend
source venv/bin/activate  # Si usas entorno virtual
python3 server.py
```

El backend expone Socket.IO en `http://localhost:5000` y el endpoint `GET /health`.

### Terminal 2 - Frontend

```bash
cd /Users/vidal/Documents/Personal/New-interface
./run_frontend.sh
```

O manualmente:
```bash
cd Frontend
npm run dev -- --host 0.0.0.0
```

El frontend estará disponible en `http://localhost:5173`

## 🌐 Acceso

Abre tu navegador en la Raspberry Pi y accede a:
```
http://localhost:5173
```

O desde otra máquina en la misma red:
```
http://[IP_DE_LA_RASPBERRY]:5173
```

## 🎯 Uso

1. **Conectar**: Haz clic en el botón de conexión en el header
2. **Seleccionar dispositivo**: Se auto-registrará el carrito disponible
3. **Mover**: Usa los joysticks para controlar movimiento y rotación
4. **Monitorear**: Observa las estadísticas y visualización en tiempo real

## 🔧 Simulación I2C

Si el dispositivo I2C no está conectado, el backend automáticamente usará **simulación**:

- Los comandos PWM se mostrarán en la consola del backend
- No se enviarán comandos físicos a los motores
- Perfecto para desarrollo y pruebas

Para usar I2C real en Raspberry Pi:

1. Habilitar I2C:
   ```bash
   sudo raspi-config
   # Interface Options -> I2C -> Enable
   ```

2. Agregar usuario al grupo i2c:
   ```bash
   sudo usermod -a -G i2c $USER
   # Reiniciar sesión
   ```

3. El backend detectará automáticamente si I2C está disponible

## 📁 Estructura del Proyecto

```
New-interface/
├── Backend/
│   ├── server.py              # Servidor FastAPI + Socket.IO (ASGI)
│   ├── requirements.txt       # Dependencias Python
│   ├── venv/                  # Entorno virtual Python
│   └── README.md              # Documentación del backend
├── Frontend/
│   ├── src/
│   │   ├── App.jsx           # Componente principal
│   │   ├── components/       # Componentes React
│   │   └── utils/
│   │       └── socket.js     # Cliente Socket.IO
│   ├── package.json
│   └── vite.config.js
├── systemd/                   # Servicios systemd para inicio automático
│   ├── robomesha-backend.service
│   └── robomesha-frontend.service
├── run_backend.sh            # Script para ejecutar backend
├── run_frontend.sh           # Script para ejecutar frontend
├── run_all.sh                # Script para iniciar todo (AP + backend + frontend)
├── install_services.sh       # Script para instalar servicios systemd
└── README.md                 # Este archivo
```

## 🔬 Lógica de Movimiento

El sistema usa **cinemática omnidireccional** para controlar 4 ruedas motorizadas:

- **vx, vy**: Velocidades lineales en X e Y (mm/s)
- **omega**: Velocidad angular (rad/s)
- **PWM**: Señales de control para cada motor (-100% a 100%)

Los cálculos están basados en el código original de RoboMesha (`firebaseconnect3.py`).

## 📝 Notas Importantes

- El backend se auto-registra como "carrito" al iniciar
- Los comandos de movimiento se procesan en tiempo real
- Si no hay movimiento durante un tiempo, los motores se detienen automáticamente
- La comunicación es bidireccional mediante WebSockets (Socket.IO)

## 🐛 Solución de Problemas

### Backend no inicia
- Verifica que Python 3.11+ esté instalado
- Instala dependencias: `pip install -r Backend/requirements.txt`
- Revisa que el puerto 5000 no esté en uso

### Frontend no se conecta
- Verifica que el backend esté corriendo en `localhost:5000`
- Revisa la consola del navegador para errores
- Verifica la configuración en `Frontend/src/utils/socket.js`

### No aparecen dispositivos
- El backend se auto-registra al iniciar
- Espera unos segundos después de iniciar el backend
- Haz clic en "Actualizar" en el frontend

### I2C no funciona
- Verifica permisos: `sudo usermod -a -G i2c $USER`
- Reinicia la sesión o ejecuta `newgrp i2c`
- Usa simulación si no necesitas I2C real

## 📚 Referencias

- [Repositorio Original RoboMesha](https://github.com/Aaronsep/RoboMesha.git)
- Documentación del backend: `Backend/README.md`

## 📄 Licencia

Ver `LICENSE.md` para más información.
