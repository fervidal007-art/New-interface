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

# ---------- Estado Global ----------

state_lock = asyncio.Lock()

operators = {}

# Sistema de comando más reciente

latest_command = None  # Último comando recibido (siempre se actualiza)

latest_command_lock = asyncio.Lock()

latest_command_time = 0

last_sent_command = None  # Último comando ENVIADO al I2C

last_send_time = 0

# Configuración

MIN_SEND_INTERVAL = 0.05  # 50ms = 20 mensajes/segundo máximo al I2C

COMMAND_TIMEOUT = 0.3     # 300ms sin comandos = detener

STOP_THRESHOLD = 0.5      # Umbral para detectar STOP

motor_task = None

safety_task = None

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

def convertir_comando_frontend(x, y, rotation):

    vx = x * V_MAX

    vy = y * V_MAX

    omega = rotation * 2.0

    return vx, vy, omega

async def motor_controller():

    """

    Tarea dedicada que procesa comandos al I2C respetando rate limiting.

    SIEMPRE procesa el comando MÁS RECIENTE, descartando todo lo demás.

    """

    global latest_command, last_sent_command, last_send_time

    

    print("[MOTOR] Controlador de motores iniciado")

    

    while True:

        await asyncio.sleep(MIN_SEND_INTERVAL)  # Esperar intervalo mínimo

        

        current_time = time.time()

        

        # Obtener el comando más reciente (thread-safe)

        async with latest_command_lock:

            comando_actual = latest_command

        

        # Si no hay comando, continuar

        if comando_actual is None:

            continue

        

        vx, vy, omega = comando_actual

        

        # Detectar si es un comando de STOP

        es_stop = (abs(vx) <= STOP_THRESHOLD and 

                   abs(vy) <= STOP_THRESHOLD and 

                   abs(omega) <= 0.1)

        

        # Crear tupla para comparación

        current_command = (round(vx, 1), round(vy, 1), round(omega, 2))

        

        # Verificar si el comando cambió

        comando_cambio = (last_sent_command != current_command)

        

        if not comando_cambio:

            # Comando idéntico al anterior, no hacer nada

            continue

        

        # El comando cambió, enviarlo al I2C

        if es_stop:

            detener_motores()

            print("[MOTOR] STOP detectado")

            last_sent_command = (0, 0, 0)

        else:

            enviar_pwm(vx, -vy, omega)

            print(f"[MOTOR] vx={vx:.1f}, vy={vy:.1f}, omega={omega:.3f}")

            last_sent_command = current_command

        

        last_send_time = current_time

async def safety_monitor():

    """

    Monitorea timeout de comandos y detiene motores si no hay actividad.

    """

    global latest_command_time, last_sent_command

    

    print(f"[SEGURIDAD] Monitor iniciado (timeout: {COMMAND_TIMEOUT}s)")

    

    while True:

        await asyncio.sleep(0.1)  # Verificar cada 100ms

        

        current_time = time.time()

        time_since_last = current_time - latest_command_time

        

        # Si pasó el timeout y los motores no están detenidos

        if time_since_last > COMMAND_TIMEOUT and last_sent_command != (0, 0, 0):

            print(f"[SEGURIDAD] ⚠️ TIMEOUT ({time_since_last:.2f}s), deteniendo motores")

            detener_motores()

            last_sent_command = (0, 0, 0)

            

            # Limpiar el comando actual

            async with latest_command_lock:

                latest_command = (0, 0, 0)

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

        'latest_command': latest_command,

        'last_sent': last_sent_command,

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

    """

    Recibe comandos del frontend y SOLO actualiza el comando más reciente.

    NO envía nada al I2C directamente - eso lo hace motor_controller()

    """

    global latest_command, latest_command_time

    

    target = data.get('target')

    payload = data.get('payload', {})

    if target != CAR_DEVICE_ID:

        return

    if payload.get('type') != 'movement':

        return

    movement = payload.get('data', {})

    vx, vy, omega = convertir_comando_frontend(

        movement.get('x', 0),

        movement.get('y', 0),

        movement.get('rotation', 0),

    )

    # SOLO actualizar el comando más reciente (thread-safe)

    async with latest_command_lock:

        latest_command = (vx, vy, omega)

        latest_command_time = time.time()

    

    # No hay rate limiting aquí - solo guardamos el comando

    # El motor_controller() se encarga de procesarlo cuando sea el momento

@sio.event

async def emergency_stop(sid, data):

    """Paro de emergencia - máxima prioridad"""

    global latest_command, latest_command_time, last_sent_command

    

    print(f"[EMERGENCIA] 🚨 PARO DE EMERGENCIA activado por {sid}")

    

    # Actualizar comando más reciente a STOP

    async with latest_command_lock:

        latest_command = (0, 0, 0)

        latest_command_time = time.time()

    

    # Detener inmediatamente (sin esperar al motor_controller)

    detener_motores()

    last_sent_command = (0, 0, 0)

    

    await sio.emit('emergency_stop_confirmed', {

        'timestamp': time.time(),

        'triggered_by': sid

    })

def cerrar_todo(signal_name, frame):

    print(f"\n[CERRANDO] Señal recibida ({signal_name}), deteniendo motores...")

    detener_motores()

    sys.exit(0)

signal.signal(signal.SIGINT, cerrar_todo)

signal.signal(signal.SIGTERM, cerrar_todo)

@fastapi_app.on_event("startup")

async def startup_event():

    """Iniciar tareas de fondo al arrancar la aplicación"""

    global motor_task, safety_task, latest_command_time

    

    latest_command_time = time.time()

    

    # Iniciar tarea de control de motores

    motor_task = asyncio.create_task(motor_controller())

    print("[INICIO] Tarea de control de motores iniciada")

    

    # Iniciar tarea de monitoreo de seguridad

    safety_task = asyncio.create_task(safety_monitor())

    print("[INICIO] Tarea de monitoreo de seguridad iniciada")

if __name__ == '__main__':

    import uvicorn

    print("=" * 60)

    print("🚀 Backend RoboMesha (ASGI) iniciando...")

    print("=" * 60)

    print(f"[I2C] Modo: {'REAL' if I2C_DISPONIBLE else 'SIMULACIÓN'}")

    print(f"[DEVICE] ID: {CAR_DEVICE_ID}")

    print(f"[CONFIG] Rate limit: {MIN_SEND_INTERVAL}s ({1/MIN_SEND_INTERVAL:.0f} msg/s)")

    print(f"[CONFIG] Timeout seguridad: {COMMAND_TIMEOUT}s")

    print(f"[SERVIDOR] Escuchando en http://0.0.0.0:5000")

    print("=" * 60)

    uvicorn.run(app, host='0.0.0.0', port=5000, log_level="info")
