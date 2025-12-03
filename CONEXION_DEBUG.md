# Guía de Diagnóstico de Conexión - RoboMesha

## Problemas Comunes y Soluciones

### 1. El frontend no se conecta al backend

#### Verificar que el backend está corriendo:
```bash
# Verificar estado del servicio
sudo systemctl status robomesha-backend

# Ver logs del backend
sudo journalctl -u robomesha-backend -f

# Verificar que está escuchando en el puerto 5000
sudo netstat -tlnp | grep 5000
# o
sudo ss -tlnp | grep 5000
```

#### Verificar conectividad:
```bash
# Desde la Raspberry Pi, probar el endpoint de health
curl http://localhost:5000/health

# Si funciona, deberías ver:
# {"status":"ok","driver_mode":"simulation","velocidad_actual":50}
```

### 2. Error: "Socket no conectado"

**Causas posibles:**
- El backend no está corriendo
- El puerto 5000 está bloqueado por firewall
- El frontend está intentando conectarse a una IP incorrecta

**Soluciones:**
1. Verificar que el backend esté corriendo:
   ```bash
   sudo systemctl start robomesha-backend
   ```

2. Verificar logs del frontend en el navegador:
   - Abre las herramientas de desarrollador (F12)
   - Ve a la pestaña "Console"
   - Busca mensajes de error o advertencias

3. Verificar la URL del backend:
   - El frontend intenta conectarse a: `http://<IP_ACTUAL>:5000`
   - Asegúrate de que el backend esté accesible en esa dirección

### 3. El backend no recibe comandos

**Verificar:**
- Los logs del backend deberían mostrar: `📥 Comando recibido de <sid>: <acción>`
- Si no ves estos mensajes, el comando no está llegando

**Solución:**
- Verifica que el frontend esté realmente conectado (debería mostrar "Conectado" en el header)
- Revisa la consola del navegador para ver si hay errores al enviar comandos

### 4. Los motores no se mueven

**Si el backend está en modo simulación:**
- Verás mensajes como: `[SIMULACIÓN] Motores moviéndose: [50, 50, 50, 50]`
- Esto significa que el I2C no está detectado o hay un error

**Para conectar hardware real:**
- Verifica que el dispositivo I2C esté conectado
- Verifica permisos I2C:
  ```bash
  sudo usermod -a -G i2c $USER
  # Luego reinicia sesión o ejecuta: newgrp i2c
  ```

- Verifica que el bus I2C esté disponible:
  ```bash
  sudo i2cdetect -y 0
  # Deberías ver 0x34 en la salida si el driver está conectado
  ```

## Comandos Útiles

### Ver logs en tiempo real
```bash
# Backend
sudo journalctl -u robomesha-backend -f

# Frontend
sudo journalctl -u robomesha-frontend -f
```

### Reiniciar servicios
```bash
sudo systemctl restart robomesha-backend
sudo systemctl restart robomesha-frontend
```

### Verificar conectividad WebSocket
Desde el navegador, abre la consola y ejecuta:
```javascript
const socket = io('http://localhost:5000');
socket.on('connect', () => console.log('✅ Conectado:', socket.id));
socket.on('connect_error', (err) => console.error('❌ Error:', err));
```

### Probar comando manualmente
Desde el navegador, en la consola:
```javascript
// Primero conéctate
const socket = io('http://localhost:5000');
socket.on('connect', () => {
  // Luego envía un comando
  socket.emit('command', { action: 'adelante' });
  console.log('Comando enviado');
});
```

## Estructura de Comandos

El backend espera comandos en este formato:
```json
{
  "action": "adelante"  // o "atras", "izquierda", "derecha", "stop", etc.
}
```

Para cambiar velocidad:
```json
{
  "action": "set_velocidad",
  "velocidad": 75
}
```

Comandos disponibles:
- `stop` - Detener todos los motores
- `adelante` - Moverse hacia adelante
- `atras` - Moverse hacia atrás
- `izquierda` - Strafe izquierda
- `derecha` - Strafe derecha
- `giro_izq` - Girar sobre el eje a la izquierda
- `giro_der` - Girar sobre el eje a la derecha
- `diag_izq_arr` - Diagonal izquierda arriba
- `diag_der_arr` - Diagonal derecha arriba
- `diag_izq_abj` - Diagonal izquierda abajo
- `diag_der_abj` - Diagonal derecha abajo


