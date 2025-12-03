"""
Backend ideal para RoboMesha con FastAPI + Socket.IO (WebSockets reales)

Controla la mesa omnidireccional vía I2C (simulado o real) y expone un API ASGI.
Integra la lógica I2C avanzada con el sistema de WebSocket del frontend.
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
    bus = smbus.SMBus(1)
    try:
        bus.write_quick(0x34)
        I2C_DISPONIBLE = True
        print("[I2C] Conexión I2C real detectada")
    except Exception:
        I2C_DISPONIBLE = False
        print("[I2C] Bus I2C no responde, usando simulación")
except ImportError:
    I2C_DISPONIBLE = False
    print("[I2C] smbus2 no disponible, usando simulación")

# ---------- Configuración HiWonder Driver I2C ----------
# Driver HiWonder para control de motores omnidireccionales
# Documentación: https://docs.hiwonder.com/

# Dirección I2C del controlador de motores
DIRECCION_MOTORES = 0x34

# Registros para velocidad fija (Fixed Speed Register)
# Este registro acepta 4 valores PWM (uno por motor) en el rango -100 a 100
REG_VELOCIDAD_FIJA = 0x33

# Registros adicionales para inicialización
MOTOR_TYPE_ADDR = 0x14
MOTOR_ENCODER_POLARITY_ADDR = 0x15
MOTOR_TYPE_JGB37_520_12V_110RPM = 3
MOTOR_ENCODER_POLARITY = 0

BUFFER_LENGTH = 32  # Tamaño del buffer circular (similar a Wire de Arduino)

# Parámetros de cinemática omnidireccional
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

# Velocidad estándar para comandos discretos (ajustable de 0 a 100)
VELOCIDAD = 50


class I2CBusWrapper:
    """
    Wrapper similar a Wire de Arduino para monitorear y debuggear I2C.
    Mantiene un buffer circular de los últimos comandos enviados.
    """

    def __init__(self, real_bus, buffer_size=BUFFER_LENGTH):
        self.bus = real_bus
        self.buffer_size = buffer_size
        self.buffer = []  # Buffer circular de comandos
        self.write_count = 0
        self.error_count = 0
        self.last_write_time = 0

    def write_i2c_block_data(self, addr, reg, data):
        """Escribe datos al I2C y actualiza el buffer de monitoreo"""
        try:
            self.bus.write_i2c_block_data(addr, reg, data)
            self.write_count += 1
            self.last_write_time = time.time()

            # Agregar al buffer circular
            buffer_entry = {
                'timestamp': time.time(),
                'addr': addr,
                'reg': reg,
                'data': data.copy() if isinstance(data, list) else data,
                'success': True
            }

            self.buffer.append(buffer_entry)
            # Mantener solo los últimos BUFFER_LENGTH comandos
            if len(self.buffer) > self.buffer_size:
                self.buffer.pop(0)

            return True
        except Exception as exc:
            self.error_count += 1
            buffer_entry = {
                'timestamp': time.time(),
                'addr': addr,
                'reg': reg,
                'data': data.copy() if isinstance(data, list) else data,
                'success': False,
                'error': str(exc)
            }
            self.buffer.append(buffer_entry)
            if len(self.buffer) > self.buffer_size:
                self.buffer.pop(0)
            raise exc

    def write_quick(self, addr):
        """Quick write (similar a Wire.beginTransmission)"""
        return self.bus.write_quick(addr)

    def write_byte_data(self, addr, reg, data):
        """Escribe un byte al I2C"""
        try:
            self.bus.write_byte_data(addr, reg, data)
            return True
        except Exception as exc:
            self.error_count += 1
            raise exc

    def read_i2c_block_data(self, addr, reg, length):
        """Lee datos del I2C"""
        try:
            return self.bus.read_i2c_block_data(addr, reg, length)
        except Exception as exc:
            self.error_count += 1
            raise exc

    def get_buffer_status(self):
        """Obtiene el estado actual del buffer (similar a Wire.available)"""
        return {
            'buffer_size': len(self.buffer),
            'buffer_capacity': self.buffer_size,
            'write_count': self.write_count,
            'error_count': self.error_count,
            'last_write_time': self.last_write_time,
            'time_since_last_write': time.time() - self.last_write_time if self.last_write_time > 0 else 0
        }

    def get_buffer_history(self, n=None):
        """Obtiene el historial del buffer (últimos n comandos)"""
        if n is None:
            return self.buffer.copy()
        return self.buffer[-n:] if n <= len(self.buffer) else self.buffer.copy()

    def clear_buffer(self):
        """Limpia el buffer (similar a Wire.flush)"""
        self.buffer.clear()
        print("[I2C] Buffer limpiado")

    def print_buffer_status(self):
        """Imprime el estado del buffer para debugging"""
        status = self.get_buffer_status()
        print(f"[I2C BUFFER] Tamaño: {status['buffer_size']}/{status['buffer_capacity']}")
        print(f"[I2C BUFFER] Escrituras: {status['write_count']}, Errores: {status['error_count']}")
        if status['last_write_time'] > 0:
            print(f"[I2C BUFFER] Última escritura hace: {status['time_since_last_write']:.3f}s")


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

    def write_byte_data(self, addr, reg, data):
        print(f"[SIMULACIÓN I2C] Escribiendo byte: {hex(addr)}, reg={hex(reg)}, data={data}")

    def write_quick(self, addr):
        pass


# Inicializar bus I2C
if not I2C_DISPONIBLE:
    bus = FakeBus()
    i2c_wrapper = None
else:
    real_bus = smbus.SMBus(0)
    i2c_wrapper = I2CBusWrapper(real_bus, buffer_size=BUFFER_LENGTH)
    bus = i2c_wrapper
    print(f"[I2C] Usando bus I2C real en dirección {hex(DIRECCION_MOTORES)}")
    print(f"[I2C] Buffer de monitoreo inicializado (tamaño: {BUFFER_LENGTH})")
    
    # Inicializar motores según documentación HiWonder
    try:
        bus.write_byte_data(DIRECCION_MOTORES, MOTOR_TYPE_ADDR, MOTOR_TYPE_JGB37_520_12V_110RPM)
        time.sleep(0.1)
        bus.write_byte_data(DIRECCION_MOTORES, MOTOR_ENCODER_POLARITY_ADDR, MOTOR_ENCODER_POLARITY)
        print("[I2C] Motores inicializados correctamente (Tipo 3, Polaridad 0)")
    except Exception as e:
        print(f"[ERROR] Fallo al inicializar motores: {e}")

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
COMMAND_TIMEOUT = 1.0      # 1 segundo sin comandos = detener (ajustado a 1 segundo)
STOP_THRESHOLD = 0.5       # Umbral para detectar STOP

motor_task = None
safety_task = None


def calcular_pwm(vx, vy, omega):
    """Calcula los valores PWM usando cinemática omnidireccional"""
    velocidades = np.dot(W, np.array([vx, vy, omega]))
    factor_escala = np.max(np.abs(velocidades)) / V_MAX if np.max(np.abs(velocidades)) > V_MAX else 1
    if factor_escala > 1:
        velocidades /= factor_escala
    velocidades[1] *= -1
    velocidades[2] *= -1
    pwm = np.clip((velocidades / V_MAX) * PWM_MAX, -PWM_MAX, PWM_MAX)
    return [int(p) for p in pwm]


def enviar_pwm(vx, vy, omega):
    """
    Envía valores PWM al driver HiWonder mediante I2C.

    El driver HiWonder espera 4 valores PWM (uno por motor) en el registro 0x33:
    - Motor 0: Delantero Izquierdo
    - Motor 1: Delantero Derecho
    - Motor 2: Trasero Derecho
    - Motor 3: Trasero Izquierdo

    Valores: -100 (máxima velocidad reversa) a 100 (máxima velocidad adelante)
    """
    pwm = calcular_pwm(vx, vy, omega)
    try:
        bus.write_i2c_block_data(DIRECCION_MOTORES, REG_VELOCIDAD_FIJA, pwm)
        # Si tenemos el wrapper, podemos monitorear el buffer
        if i2c_wrapper is not None and i2c_wrapper.write_count % 50 == 0:
            # Imprimir estado del buffer cada 50 escrituras
            i2c_wrapper.print_buffer_status()
    except Exception as exc:
        print(f"[ERROR] Error al enviar PWM al driver HiWonder: {exc}")
        if i2c_wrapper is not None:
            print(f"[I2C BUFFER] Errores totales: {i2c_wrapper.error_count}")


def detener_motores():
    """
    Detiene todos los motores enviando PWM = 0 a todos los motores.
    Compatible con driver HiWonder.
    """
    try:
        bus.write_i2c_block_data(DIRECCION_MOTORES, REG_VELOCIDAD_FIJA, [0, 0, 0, 0])
        print("[MOTORES] Todos los motores detenidos (HiWonder)")
    except Exception as exc:
        print(f"[ERROR] Error al detener motores en HiWonder: {exc}")


def convertir_comando_frontend(x, y, rotation):
    """Convierte comandos del frontend (normalizados -1 a 1) a velocidades físicas"""
    vx = x * V_MAX
    vy = y * V_MAX
    omega = rotation * 2.0
    return vx, vy, omega


# ---------- Comandos discretos (compatibilidad con botones) ----------
def convertir_accion_a_velocidades(accion):
    """
    Convierte una acción discreta (adelante, atras, etc.) a velocidades vx, vy, omega.
    Retorna (vx, vy, omega) o None si la acción no es válida.
    """
    # Mapeo de acciones a velocidades normalizadas
    acciones = {
        "stop": (0, 0, 0),
        "adelante": (0, 1, 0),  # vx=0, vy=1 (adelante), omega=0
        "atras": (0, -1, 0),    # vx=0, vy=-1 (atrás), omega=0
        "izquierda": (-1, 0, 0),  # vx=-1 (izquierda), vy=0, omega=0
        "derecha": (1, 0, 0),   # vx=1 (derecha), vy=0, omega=0
        "giro_izq": (0, 0, -1),  # vx=0, vy=0, omega=-1 (rotación izquierda)
        "giro_der": (0, 0, 1),   # vx=0, vy=0, omega=1 (rotación derecha)
        "diag_izq_arr": (-0.707, 0.707, 0),  # Diagonal superior izquierda
        "diag_der_arr": (0.707, 0.707, 0),   # Diagonal superior derecha
        "diag_izq_abj": (-0.707, -0.707, 0),  # Diagonal inferior izquierda
        "diag_der_abj": (0.707, -0.707, 0),   # Diagonal inferior derecha
    }
    
    if accion not in acciones:
        return None
    
    x_norm, y_norm, rot_norm = acciones[accion]
    return convertir_comando_frontend(x_norm, y_norm, rot_norm)


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
            enviar_pwm(vx, vy, omega)
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
    """Emite la lista de dispositivos disponibles"""
    data = {'devices': [CAR_DEVICE_ID]}
    if target_sid:
        await sio.emit('device_list', data, to=target_sid)
    else:
        await sio.emit('device_list', data)
    print(f"[DEVICES] Lista actualizada: {data['devices']}")


# ---------- Endpoints FastAPI ----------
@fastapi_app.get('/health')
async def health_check():
    response = {
        'status': 'ok',
        'mode': 'REAL' if I2C_DISPONIBLE else 'SIMULACION',
        'device': CAR_DEVICE_ID,
        'latest_command': latest_command,
        'last_sent': last_sent_command,
    }

    # Agregar información del buffer I2C si está disponible
    if i2c_wrapper is not None:
        response['i2c_buffer'] = i2c_wrapper.get_buffer_status()

    return response


@fastapi_app.get('/i2c/buffer')
async def get_i2c_buffer(n: int = 10):
    """
    Obtiene el historial del buffer I2C (últimos n comandos).
    Similar a revisar Wire.available() y el buffer en Arduino.
    """
    if not I2C_DISPONIBLE or i2c_wrapper is None:
        return {
            'error': 'I2C no disponible o en modo simulación',
            'mode': 'SIMULACION'
        }

    status = i2c_wrapper.get_buffer_status()
    history = i2c_wrapper.get_buffer_history(n)

    return {
        'status': status,
        'history': history,
        'buffer_length': BUFFER_LENGTH
    }


@fastapi_app.post('/i2c/buffer/clear')
async def clear_i2c_buffer():
    """Limpia el buffer I2C (similar a Wire.flush())"""
    if not I2C_DISPONIBLE or i2c_wrapper is None:
        return {'error': 'I2C no disponible o en modo simulación'}

    i2c_wrapper.clear_buffer()
    return {'status': 'Buffer limpiado exitosamente'}


# ---------- Eventos Socket.IO ----------
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
    # Seguridad: detener motores si se desconecta el operador
    detener_motores()


@sio.event
async def register(sid, data):
    """Registra un operador en el sistema"""
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
    """Solicita la lista de dispositivos disponibles"""
    await emit_device_list(target_sid=sid)


@sio.event
async def send_command(sid, data):
    """
    Recibe comandos del frontend y SOLO actualiza el comando más reciente.
    NO envía nada al I2C directamente - eso lo hace motor_controller()

    Espera: {target: "carrito_...", payload: {type: "movement", data: {x, y, rotation}}}
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
async def command(sid, data):
    """
    Recibe comandos discretos del frontend (compatibilidad con botones).
    Espera: {"action": "adelante"} o {"action": "stop"}
    """
    global latest_command, latest_command_time
    accion = data.get("action")

    if accion is None:
        return

    # Convertir acción a velocidades
    velocidades = convertir_accion_a_velocidades(accion)
    if velocidades is None:
        print(f"[COMANDO] Acción desconocida: {accion}")
        return

    vx, vy, omega = velocidades

    # Actualizar el comando más reciente (thread-safe)
    async with latest_command_lock:
        latest_command = (vx, vy, omega)
        latest_command_time = time.time()

    print(f"[COMANDO] Acción '{accion}' -> vx={vx:.1f}, vy={vy:.1f}, omega={omega:.3f}")


@sio.event
async def emergency_stop(sid, data):
    """Paro de emergencia - máxima prioridad"""
    global latest_command, latest_command_time, last_sent_command
    print(f"[EMERGENCIA] 🚨 PARO DE EMERGENCIA activado por {sid}")
    # Actualizar comando más reciente a STOP (0, 0, 0)
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
    """Maneja señales de cierre (SIGINT, SIGTERM)"""
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
