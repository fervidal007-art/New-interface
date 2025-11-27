"""
Backend ideal para RoboMesha con FastAPI + Socket.IO (WebSockets reales)
Controla la mesa omnidireccional vía I2C (simulado o real) y expone un API ASGI.
"""

import asyncio
import signal
import socket
import sys
import time
import uuid

import numpy as np
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ---------- Inicialización I2C ----------
try:
    import smbus2 as smbus

    bus = smbus.SMBus(0)
    try:
        bus.write_quick(0x34)
        I2C_DISPONIBLE = True
        print("[I2C] Conexión I2C real detectada")
    except Exception:
        I2C_DISPONIBLE = False
        print("[I2C] Bus I2C no responde, usando simulación")
except ImportError:
    I2C_DISPONIBLE = False
    print("[I2C] smbus0 no disponible, usando simulación")

DIRECCION_MOTORES = 0x34
REG_VELOCIDAD_FIJA = 0x33
REG_LEER_ENCODERS = 0x30  # Registro para leer velocidades de encoders

R = 0.048
l1 = 0.097
l2 = 0.109
W = (1 / R) * np.array([
    [1, 1, -(l1 + l2)],
    [1, 1, (l1 + l2)],
    [1, -1, (l1 + l2)],
    [1, -1, -(l1 + l2)],
])
V_MAX = 250
PWM_MAX = 100


class FakeBus:
    def write_i2c_block_data(self, addr, reg, data):
        motor_names = [
            'Motor Delantero Izquierdo',
            'Motor Delantero Derecho',
            'Motor Trasero Derecho',
            'Motor Trasero Izquierdo',
        ]
        print("[SIMULACIÓN I2C] Comando enviado:")
        print(f"  Dirección: {hex(addr)}, Registro: {hex(reg)}")
        for name, pwm in zip(motor_names, data):
            print(f"  {name}: PWM = {pwm:6.2f}")
    
    def read_i2c_block_data(self, addr, reg, length):
        # Simular lectura de encoders (valores ficticios)
        return [0] * length


if not I2C_DISPONIBLE:
    bus = FakeBus()
else:
    print(f"[I2C] Usando bus I2C real en dirección {hex(DIRECCION_MOTORES)}")


# ---------- Aplicación ASGI ----------
HOSTNAME = socket.gethostname()
CAR_DEVICE_ID = f"carrito_{HOSTNAME}"

fastapi_app = FastAPI(title="RoboMesha Backend", version="1.0.0")
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    ping_interval=10,
    ping_timeout=30,
)
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

state_lock = asyncio.Lock()
operators = {}
last_command = None


def calcular_pwm(vx, vy, omega):
    velocidades = np.dot(W, np.array([vx, vy, omega]))
    factor_escala = np.max(np.abs(velocidades)) / V_MAX if np.max(np.abs(velocidades)) > V_MAX else 1
    if factor_escala > 1:
        velocidades /= factor_escala

    velocidades[1] *= -1
    velocidades[2] *= -1

    pwm = np.clip((velocidades / V_MAX) * PWM_MAX, -PWM_MAX, PWM_MAX)
    return [int(p) for p in pwm]


def enviar_pwm(vx, vy, omega):
    pwm = calcular_pwm(vx, vy, omega)
    try:
        bus.write_i2c_block_data(DIRECCION_MOTORES, REG_VELOCIDAD_FIJA, pwm)
    except Exception as exc:
        print(f"[ERROR] Error al enviar PWM: {exc}")


def detener_motores():
    try:
        bus.write_i2c_block_data(DIRECCION_MOTORES, REG_VELOCIDAD_FIJA, [0, 0, 0, 0])
        print("[MOTORES] Todos los motores detenidos")
    except Exception as exc:
        print(f"[ERROR] Error al detener motores: {exc}")


def leer_velocidades_encoders():
    """Lee las velocidades de los 4 encoders desde el Arduino vía I2C.
    Retorna un array de 4 valores con las velocidades en RPM o cuentas por segundo.
    """
    try:
        # Leer 16 bytes: 4 floats de 4 bytes cada uno (velocidad de cada motor)
        data = bus.read_i2c_block_data(DIRECCION_MOTORES, REG_LEER_ENCODERS, 16)
        
        # Convertir bytes a floats (little-endian)
        import struct
        velocidades = []
        for i in range(4):
            bytes_motor = data[i*4:(i+1)*4]
            velocidad = struct.unpack('<f', bytes(bytes_motor))[0]
            velocidades.append(velocidad)
        
        return velocidades
    except Exception as exc:
        print(f"[ERROR] Error al leer encoders: {exc}")
        return [0.0, 0.0, 0.0, 0.0]


def convertir_comando_frontend(x, y, rotation):
    vx = x * V_MAX
    vy = y * V_MAX
    omega = rotation * 2.0
    return vx, vy, omega


async def emit_device_list(target_sid=None):
    data = {'devices': [CAR_DEVICE_ID]}
    if target_sid:
        await sio.emit('device_list', data, to=target_sid)
    else:
        await sio.emit('device_list', data)
    print(f"[DEVICES] Lista actualizada: {data['devices']}")


@fastapi_app.get('/health')
async def health_check():
    return {
        'status': 'ok',
        'mode': 'REAL' if I2C_DISPONIBLE else 'SIMULACION',
        'device': CAR_DEVICE_ID,
        'last_command': last_command,
    }


@sio.event
async def connect(sid, environ, auth):
    print(f"[CONEXIÓN] Operador conectado: {sid}")
    await emit_device_list(target_sid=sid)


@sio.event
async def disconnect(sid):
    async with state_lock:
        if sid in operators:
            operator = operators.pop(sid)
            print(f"[CONEXIÓN] Operador desconectado: {operator['name']} ({sid})")
        else:
            print(f"[CONEXIÓN] Cliente desconectado: {sid}")


@sio.event
async def register(sid, data):
    name = data.get('base_name', 'unknown')
    role = data.get('role', 'operator')
    async with state_lock:
        operators[sid] = {
            'name': name,
            'role': role,
            'connected_at': time.time(),
            'device_id': f"operator_{name}_{uuid.uuid4().hex[:6]}",
        }
    print(f"[REGISTRO] {name} ({role}) registrado - SID: {sid}")
    await emit_device_list(target_sid=sid)


@sio.event
async def list_devices(sid):
    await emit_device_list(target_sid=sid)


@sio.event
async def send_command(sid, data):
    global last_command
    target = data.get('target')
    payload = data.get('payload', {})

    if target != CAR_DEVICE_ID:
        print(f"[COMANDO] Target desconocido ({target}), ignorando")
        return

    if payload.get('type') != 'movement':
        print(f"[COMANDO] Tipo no soportado: {payload.get('type')}")
        return

    movement = payload.get('data', {})
    x_raw = movement.get('x', 0)
    y_raw = movement.get('y', 0)
    rotation_raw = movement.get('rotation', 0)
    
    # Si los valores son exactamente 0, detener motores inmediatamente
    if x_raw == 0 and y_raw == 0 and rotation_raw == 0:
        detener_motores()
        last_command = {'vx': 0, 'vy': 0, 'omega': 0, 'ts': movement.get('timestamp')}
        
        # Leer y mostrar velocidades de encoders
        velocidades = leer_velocidades_encoders()
        print(f"[ENCODERS] Velocidades: FL={velocidades[0]:.2f}, FR={velocidades[1]:.2f}, "
              f"RR={velocidades[2]:.2f}, RL={velocidades[3]:.2f}")
        return
    
    vx, vy, omega = convertir_comando_frontend(x_raw, y_raw, rotation_raw)

    # Umbrales más altos para evitar movimientos accidentales
    if abs(vx) > 5.0 or abs(vy) > 5.0 or abs(omega) > 0.1:
        enviar_pwm(vx, vy, omega)
        last_command = {'vx': vx, 'vy': vy, 'omega': omega, 'ts': movement.get('timestamp')}
        print(f"[COMANDO] vx={vx:.1f} mm/s, vy={vy:.1f} mm/s, omega={omega:.3f} rad/s")
    else:
        detener_motores()
        last_command = {'vx': 0, 'vy': 0, 'omega': 0, 'ts': movement.get('timestamp')}


def cerrar_todo(signal_name, frame):
    print(f"\n[CERRANDO] Señal recibida ({signal_name}), deteniendo motores...")
    detener_motores()
    sys.exit(0)


signal.signal(signal.SIGINT, cerrar_todo)
signal.signal(signal.SIGTERM, cerrar_todo)


if __name__ == '__main__':
    import uvicorn

    print("=" * 60)
    print("🚀 Backend RoboMesha (ASGI) iniciando...")
    print("=" * 60)
    print(f"[I2C] Modo: {'REAL' if I2C_DISPONIBLE else 'SIMULACIÓN'}")
    print(f"[DEVICE] ID: {CAR_DEVICE_ID}")
    print(f"[SERVIDOR] Escuchando en http://0.0.0.0:5000")
    print("=" * 60)

    uvicorn.run(app, host='0.0.0.0', port=5000, log_level="info")
