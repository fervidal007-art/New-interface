# Backend RoboMesha

Backend en Python para controlar la mesa robótica RoboMesha mediante comunicación I2C (simulada o real).

## Características

- ✅ Comunicación con frontend mediante Socket.IO
- ✅ Control de motores omnidireccionales mediante I2C
- ✅ Simulación de I2C cuando el dispositivo no está conectado
- ✅ Cálculo de PWM basado en cinemática omnidireccional
- ✅ Auto-registro de carritos disponibles

## Requisitos

- Python 3.8 o superior
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

### Ejecutar el servidor

```bash
python3 server.py
```

El servidor se iniciará en `http://localhost:5000` y escuchará conexiones Socket.IO.

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

### Eventos recibidos del cliente:

- `connect`: Cliente se conecta (auto-registro como carrito)
- `disconnect`: Cliente se desconecta
- `register`: Registrar dispositivo con rol específico
- `list_devices`: Solicitar lista de dispositivos disponibles
- `send_command`: Enviar comando de movimiento

### Eventos enviados al cliente:

- `connected`: Confirmación de conexión con device_id
- `device_list`: Lista de carritos disponibles `{devices: ["carrito_..."]}`
- `device_list` (broadcast): Lista actualizada cuando hay cambios

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

