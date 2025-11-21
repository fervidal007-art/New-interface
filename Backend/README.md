# Backend RoboMesha

Backend ASGI construido con FastAPI + Socket.IO para controlar la mesa RoboMesha mediante comunicación I2C (simulada o real).

## Características

- ✅ Comunicación en tiempo real (WebSockets reales) con Socket.IO
- ✅ Control de motores omnidireccionales mediante I2C
- ✅ Simulación de I2C cuando el dispositivo no está conectado
- ✅ Cálculo de PWM basado en cinemática omnidireccional
- ✅ API REST `/health` para monitoreo

## Requisitos

- Python 3.11+ (probado en Raspberry Pi OS Bookworm)
- Dependencias listadas en `requirements.txt`

## Instalación

### 1. Crear entorno virtual (recomendado)

```bash
cd Backend
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

## Uso

### Ejecutar el servidor (UVicorn)

```bash
python3 server.py
# o
uvicorn Backend.server:app --host 0.0.0.0 --port 5000
```

El servidor expone:
- WebSocket/Socket.IO en `ws://<ip>:5000/socket.io/`
- Endpoint `GET /health` para monitoreo básico

### Simulación vs I2C Real

El backend detecta automáticamente si el dispositivo I2C está disponible:

- **I2C Real**: Si `smbus2` está instalado y el bus I2C responde, usará comunicación real.
- **Simulación**: Si no está disponible, mostrará los comandos PWM en la consola sin enviarlos físicamente.

## Configuración de Motores

Los parámetros de cinemática están configurados en `server.py`:

- `R = 0.048`: Radio de la rueda (metros)
- `l1 = 0.097`: Distancia del centro al eje delantero
- `l2 = 0.109`: Distancia del centro al eje trasero
- `V_MAX = 250`: Velocidad máxima (mm/s)
- `PWM_MAX = 100`: PWM máximo (%)
- `DIRECCION_MOTORES = 0x34`: Dirección I2C del controlador de motores
- `REG_VELOCIDAD_FIJA = 0x33`: Registro para velocidad fija

## Estructura de Comandos

El frontend envía comandos con el siguiente formato:

```json
{
  "target": "device_id",
  "payload": {
    "type": "movement",
    "data": {
      "x": -1.0 a 1.0,      // Movimiento en X (normalizado)
      "y": -1.0 a 1.0,      // Movimiento en Y (normalizado)
      "rotation": -1.0 a 1.0, // Rotación (normalizado)
      "timestamp": 1234567890
    }
  }
}
```

El backend convierte estos valores a velocidades (vx, vy, omega) y calcula los valores PWM para los 4 motores.

## Eventos Socket.IO

| Evento             | Dirección | Descripción |
|--------------------|-----------|-------------|
| `connect`          | Cliente→Servidor | Vincula al operador y recibe la lista de dispositivos |
| `register`         | Cliente→Servidor | Identifica al operador (`role`, `base_name`) |
| `list_devices`     | Cliente→Servidor | Solicita la lista de carritos disponibles |
| `send_command`     | Cliente→Servidor | Envía comando de movimiento (`x`, `y`, `rotation`) |
| `device_list`      | Servidor→Cliente | Lista `[carrito_hostname]` disponible |
| `conversation_message` (pendiente) | Servidor→Cliente | Canal opcional para logs |

## Notas para Raspberry Pi

1. **Permisos I2C**: En Raspberry Pi, asegúrate de tener permisos para acceder al bus I2C:
   ```bash
   sudo usermod -a -G i2c $USER
   ```

2. **Habilitar I2C**: Si no está habilitado:
   ```bash
   sudo raspi-config
   # Interface Options -> I2C -> Enable
   ```

3. **Instalar smbus2**: Para comunicación I2C real:
   ```bash
   pip install smbus2
   ```

## Solución de Problemas

- **Error de permisos I2C**: Asegúrate de estar en el grupo `i2c`
- **No detecta dispositivos**: Verifica que el frontend esté conectado correctamente
- **Motores no responden**: Verifica la dirección I2C y el registro configurados

