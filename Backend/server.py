"""
Backend Optimizado para RoboMesha - Hiwonder Driver
Basado en documentación oficial: TankDemo.py y PDF de desarrollo.
"""
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
try:
    from smbus2 import SMBus
except ImportError:
    # Fallback para sistemas que no tienen smbus2 instalado
    SMBus = None
import time
import struct

# --- CONFIGURACIÓN I2C OFICIAL ---
# Basado en [cite: 92, 93]
I2C_BUS = 1
MOTOR_ADDR = 0x34 

# Registros (TankDemo.py)
ADC_BAT_ADDR = 0x00
MOTOR_TYPE_ADDR = 0x14 
MOTOR_ENCODER_POLARITY_ADDR = 0x15 
MOTOR_FIXED_PWM_ADDR = 0x1F 
MOTOR_FIXED_SPEED_ADDR = 0x33 # Control de velocidad (Closed Loop) [cite: 99]

# Configuración de Motores JGB37-520 (Mecanum)
# [cite: 111, 112]
MOTOR_TYPE_JGB37_520_12V_110RPM = 3 
MOTOR_ENCODER_POLARITY = 0

# Velocidad estándar para los movimientos (Ajustable de 0 a 100)
VELOCIDAD = 50 

class HiwonderDriver:
    def __init__(self):
        self.bus = None
        self.simulation_mode = False
        try:
            if SMBus is None:
                raise ImportError("smbus2 no está instalado")
            self.bus = SMBus(I2C_BUS)
            print(f"[INIT] Conexión I2C exitosa en bus {I2C_BUS}")
            self.init_motors()
        except Exception as e:
            print(f"[ERROR] No se detectó I2C ({e}). Usando MODO SIMULACIÓN.")
            self.simulation_mode = True

    def init_motors(self):
        """Inicializa el driver como pide la documentación oficial [cite: 123, 125]"""
        if self.simulation_mode: return
        try:
            # 1. Configurar tipo de motor
            self.bus.write_byte_data(MOTOR_ADDR, MOTOR_TYPE_ADDR, MOTOR_TYPE_JGB37_520_12V_110RPM)
            time.sleep(0.1) # Pequeña pausa necesaria
            # 2. Configurar polaridad
            self.bus.write_byte_data(MOTOR_ADDR, MOTOR_ENCODER_POLARITY_ADDR, MOTOR_ENCODER_POLARITY)
            print("[INIT] Motores inicializados correctamente (Tipo 3, Polaridad 0).")
        except Exception as e:
            print(f"[ERROR] Fallo al inicializar motores: {e}")

    def enviar_velocidad(self, velocidades):
        """
        Envía el array de 4 velocidades al registro 0x33 (Fixed Speed)
        velocidades: lista de 4 enteros [m1, m2, m3, m4]
        
        """
        if self.simulation_mode:
            print(f"[SIMULACIÓN] Motores moviéndose: {velocidades}")
            return

        try:
            # Escribir bloque I2C al registro 0x33
            self.bus.write_i2c_block_data(MOTOR_ADDR, MOTOR_FIXED_SPEED_ADDR, velocidades)
            # NO ponemos sleep aquí para no bloquear el servidor, el driver se encarga.
        except Exception as e:
            print(f"[I2C ERROR] No se pudo enviar comando: {e}")

# Instancia del driver
driver = HiwonderDriver()

# --- LÓGICA DE MOVIMIENTOS MECANUM ---
# Asumiendo mapeo: M1=FrontIzq, M2=TrasIzq, M3=FrontDer, M4=TrasDer (Verificar cableado)
# Si un motor gira al revés, invierte el signo aquí.

def detener():
    print(">> DETENER")
    driver.enviar_velocidad([0, 0, 0, 0])

def adelante():
    # Todos positivos (o ajustar según cableado)
    v = [VELOCIDAD, VELOCIDAD, VELOCIDAD, VELOCIDAD] 
    print(f">> ADELANTE {v}")
    driver.enviar_velocidad(v)

def atras():
    # Todos negativos
    v = [-VELOCIDAD, -VELOCIDAD, -VELOCIDAD, -VELOCIDAD]
    print(f">> ATRAS {v}")
    driver.enviar_velocidad(v)

def derecha():
    # Strafe Izquierda: M1(-), M2(+), M3(+), M4(-)
    v = [-VELOCIDAD, VELOCIDAD, VELOCIDAD, -VELOCIDAD]
    print(f">> IZQUIERDA {v}")
    driver.enviar_velocidad(v)

def izquierda():
    # Strafe Derecha: M1(+), M2(-), M3(-), M4(+)
    v = [VELOCIDAD, -VELOCIDAD, -VELOCIDAD, VELOCIDAD]
    print(f">> DERECHA {v}")
    driver.enviar_velocidad(v)

def giro_derecha():
    # Girar sobre su eje a la izquierda: Izquierdos(-), Derechos(+)
    v = [-VELOCIDAD, VELOCIDAD, -VELOCIDAD, VELOCIDAD]
    print(f">> GIRO IZQ {v}")
    driver.enviar_velocidad(v)

def giro_izquierda():
    # Girar sobre su eje a la derecha: Izquierdos(+), Derechos(-)
    v = [VELOCIDAD, -VELOCIDAD, VELOCIDAD, -VELOCIDAD]
    print(f">> GIRO DER {v}")
    driver.enviar_velocidad(v)

# --- DIAGONALES (Solo mueven 2 ruedas) ---
def diagonal_der_arriba():
    # M1(0), M2(+), M3(+), M4(0)
    v = [0, VELOCIDAD, VELOCIDAD, 0]
    print(f">> DIAG IZQ ARRIBA {v}")
    driver.enviar_velocidad(v)

def diagonal_izq_arriba():
    # M1(+), M2(0), M3(0), M4(+)
    v = [VELOCIDAD, 0, 0, VELOCIDAD]
    print(f">> DIAG DER ARRIBA {v}")
    driver.enviar_velocidad(v)

def diagonal_der_abajo():
    # M1(-), M2(0), M3(0), M4(-)
    v = [-VELOCIDAD, 0, 0, -VELOCIDAD]
    print(f">> DIAG IZQ ABAJO {v}")
    driver.enviar_velocidad(v)

def diagonal_izq_abajo():
    # M1(0), M2(-), M3(-), M4(0)
    v = [0, -VELOCIDAD, -VELOCIDAD, 0]
    print(f">> DIAG DER ABAJO {v}")
    driver.enviar_velocidad(v)

# Diccionario de comandos para mapear texto a función
COMANDOS = {
    "stop": detener,
    "adelante": adelante,
    "atras": atras,
    "izquierda": izquierda,
    "derecha": derecha,
    "giro_izq": giro_izquierda,
    "giro_der": giro_derecha,
    "diag_izq_arr": diagonal_izq_arriba,
    "diag_der_arr": diagonal_der_arriba,
    "diag_izq_abj": diagonal_izq_abajo,
    "diag_der_abj": diagonal_der_abajo
}

# --- SERVIDOR FASTAPI + SOCKET.IO ---
app_fastapi = FastAPI()

# Configurar CORS para permitir conexión desde React/Vite
app_fastapi.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint de health check
@app_fastapi.get("/health")
async def health_check():
    """Endpoint para verificar que el servidor está funcionando"""
    return {
        "status": "ok",
        "service": "RoboMesha Backend",
        "socketio": "available",
        "i2c_mode": "simulation" if driver.simulation_mode else "real"
    }

# Configurar Socket.IO con CORS explícito y opciones adicionales
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e6
)
app = socketio.ASGIApp(sio, other_asgi_app=app_fastapi)

# --- GESTIÓN DE DISPOSITIVOS Y CLIENTES ---
# Almacenar información de clientes conectados
connected_clients = {}  # {sid: {role, name, device_name}}
registered_devices = {}  # {device_name: {sid, role, last_seen}}

# Nombre del dispositivo principal (el robot físico)
ROBOT_DEVICE_NAME = "RoboMesha"

@sio.event
async def connect(sid, environ):
    """Maneja la conexión de nuevos clientes"""
    print(f"[CONNECT] Cliente conectado: {sid}")
    connected_clients[sid] = {
        'role': None,
        'name': None,
        'device_name': None,
        'connected_at': time.time()
    }

@sio.event
async def disconnect(sid):
    """Maneja la desconexión de clientes"""
    print(f"[DISCONNECT] Cliente desconectado: {sid}")
    
    # Si era un operador, detener el robot por seguridad
    client_info = connected_clients.get(sid, {})
    if client_info.get('role') == 'operator':
        print("[SEGURIDAD] Operador desconectado, deteniendo robot")
        detener()
    
    # Limpiar registros
    if sid in connected_clients:
        device_name = connected_clients[sid].get('device_name')
        if device_name and device_name in registered_devices:
            del registered_devices[device_name]
        del connected_clients[sid]
    
    # Notificar a otros clientes sobre la actualización de dispositivos
    await broadcast_device_list()

@sio.event
async def register(sid, data):
    """
    Registra un cliente como operador o dispositivo.
    Data esperado: {"role": "operator", "base_name": "ControlPanel"}
    """
    role = data.get("role", "unknown")
    base_name = data.get("base_name", "Unknown")
    
    # Generar nombre único si es necesario
    if role == "operator":
        device_name = f"{base_name}_{sid[:8]}"
    else:
        device_name = base_name
    
    # Actualizar información del cliente
    if sid in connected_clients:
        connected_clients[sid].update({
            'role': role,
            'name': base_name,
            'device_name': device_name
        })
    
    # Registrar dispositivo
    registered_devices[device_name] = {
        'sid': sid,
        'role': role,
        'name': base_name,
        'last_seen': time.time()
    }
    
    print(f"[REGISTER] {role} registrado: {device_name} (sid: {sid})")
    
    # Confirmar registro
    await sio.emit('registered', {
        'name': device_name,
        'role': role,
        'base_name': base_name
    }, room=sid)
    
    # Enviar lista actualizada de dispositivos
    await broadcast_device_list()

@sio.event
async def list_devices(sid, data=None):
    """
    Responde con la lista de dispositivos registrados.
    """
    device_list = list(registered_devices.keys())
    # Siempre incluir el robot principal en la lista
    if ROBOT_DEVICE_NAME not in device_list:
        device_list.append(ROBOT_DEVICE_NAME)
    print(f"[LIST_DEVICES] Enviando lista a {sid}: {device_list}")
    
    await sio.emit('device_list', {
        'devices': device_list
    }, room=sid)

@sio.event
async def command(sid, data):
    """
    Recibe comandos simples desde el frontend.
    Data esperado: {"action": "adelante"} o {"action": "stop"}
    """
    accion = data.get("action")
    
    # Verificar que el cliente está registrado como operador
    client_info = connected_clients.get(sid, {})
    if client_info.get('role') != 'operator':
        print(f"[WARNING] Cliente {sid} intentó enviar comando sin ser operador")
        await sio.emit('error', {
            'message': 'No autorizado: solo operadores pueden enviar comandos'
        }, room=sid)
        return
    
    print(f"[COMMAND] Comando recibido de {sid}: {accion}")
    
    if accion in COMANDOS:
        # Ejecutar la función correspondiente (usa I2C)
        COMANDOS[accion]()
        
        # Enviar mensaje de conversación para logging
        await send_conversation_message(
            device=ROBOT_DEVICE_NAME,
            direction='incoming',
            payload={'action': accion, 'type': 'command'},
            origin=client_info.get('device_name', 'unknown')
        )
        
        # Confirmar recepción
        await sio.emit('command_received', {
            'action': accion,
            'status': 'executed'
        }, room=sid)
    else:
        print(f"[ERROR] Comando desconocido: {accion}")
        await sio.emit('error', {
            'message': f'Comando desconocido: {accion}'
        }, room=sid)

@sio.event
async def send_command(sid, data):
    """
    Envía un comando a un dispositivo específico.
    Data esperado: {"target": "RoboMesha", "payload": {...}}
    """
    target = data.get("target")
    payload = data.get("payload", {})
    
    # Verificar que el cliente está registrado como operador
    client_info = connected_clients.get(sid, {})
    if client_info.get('role') != 'operator':
        print(f"[WARNING] Cliente {sid} intentó enviar comando sin ser operador")
        await sio.emit('error', {
            'message': 'No autorizado: solo operadores pueden enviar comandos'
        }, room=sid)
        return
    
    print(f"[SEND_COMMAND] Comando a {target} desde {sid}: {payload}")
    
    # Si el target es el robot principal, procesar el comando
    if target == ROBOT_DEVICE_NAME:
        # Procesar comando de movimiento
        if payload.get('type') == 'movement':
            movement_data = payload.get('data', {})
            x = movement_data.get('x', 0)
            y = movement_data.get('y', 0)
            rotation = movement_data.get('rotation', 0)
            
            # Convertir coordenadas a comandos de movimiento mecanum
            await process_movement_command(x, y, rotation)
        
        # Enviar mensaje de conversación
        await send_conversation_message(
            device=target,
            direction='incoming',
            payload=payload,
            origin=client_info.get('device_name', 'unknown')
        )
    
    # Si el target existe en dispositivos registrados, reenviar
    elif target in registered_devices:
        target_sid = registered_devices[target]['sid']
        await sio.emit('command', payload, room=target_sid)
    
    # Confirmar envío
    await sio.emit('command_sent', {
        'target': target,
        'payload': payload
    }, room=sid)

async def process_movement_command(x, y, rotation):
    """
    Procesa comandos de movimiento con coordenadas x, y, rotation.
    Convierte a velocidades de motores mecanum.
    """
    # Normalizar valores
    x = max(-1, min(1, x))
    y = max(-1, min(1, y))
    rotation = max(-1, min(1, rotation))
    
    # Calcular velocidades para cada motor (mecanum)
    # M1=FrontIzq, M2=TrasIzq, M3=FrontDer, M4=TrasDer
    # Fórmula mecanum: v = x + y + rotation
    m1 = (x + y + rotation) * VELOCIDAD
    m2 = (-x + y + rotation) * VELOCIDAD
    m3 = (-x + y - rotation) * VELOCIDAD
    m4 = (x + y - rotation) * VELOCIDAD
    
    # Limitar valores a rango [-100, 100]
    velocidades = [
        int(max(-100, min(100, m1))),
        int(max(-100, min(100, m2))),
        int(max(-100, min(100, m3))),
        int(max(-100, min(100, m4)))
    ]
    
    print(f"[MOVEMENT] x={x:.2f}, y={y:.2f}, rot={rotation:.2f} -> {velocidades}")
    driver.enviar_velocidad(velocidades)

async def send_conversation_message(device, direction, payload, origin):
    """
    Envía un mensaje de conversación a todos los clientes conectados.
    """
    message = {
        'device': device,
        'direction': direction,
        'payload': payload,
        'origin': origin,
        'ts': time.time()
    }
    
    # Broadcast a todos los clientes
    await sio.emit('conversation_message', message)

async def broadcast_device_list():
    """
    Envía la lista actualizada de dispositivos a todos los clientes.
    """
    device_list = list(registered_devices.keys())
    # Siempre incluir el robot principal en la lista
    if ROBOT_DEVICE_NAME not in device_list:
        device_list.append(ROBOT_DEVICE_NAME)
    await sio.emit('device_list', {
        'devices': device_list
    })

# Registrar el robot principal como dispositivo disponible desde el inicio
# (no tiene un sid porque es el servidor mismo)
registered_devices[ROBOT_DEVICE_NAME] = {
    'sid': None,  # El servidor mismo
    'role': 'robot',
    'name': ROBOT_DEVICE_NAME,
    'last_seen': time.time()
}

if __name__ == '__main__':
    print("🚀 Iniciando servidor RoboMesha...")
    print(f"🤖 Robot registrado: {ROBOT_DEVICE_NAME}")
    print("📡 Escuchando en 0.0.0.0:5000 (todas las interfaces)")
    print("🔌 Esperando conexiones de clientes...")
    print("🌐 Socket.IO disponible en: ws://0.0.0.0:5000/socket.io/")
    uvicorn.run(
        app, 
        host='0.0.0.0', 
        port=5000,
        log_level='info',
        access_log=True
    )