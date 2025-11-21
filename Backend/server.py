"""
Backend para control de RoboMesha
Comunica el frontend con los motores mediante I2C (simulado o real)
"""

import time
import socket
import uuid
import numpy as np
import signal
import sys
from flask import Flask, request
from flask_socketio import SocketIO, emit
from threading import Lock

# Intento importar smbus2 para I2C real, si no está disponible usamos simulación
try:
    import smbus2 as smbus
    bus = smbus.SMBus(1)
    # Probar si el bus responde
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

# Configuración de motores (de firebaseconnect3.py)
DIRECCION_MOTORES = 0x34
REG_VELOCIDAD_FIJA = 0x33

# Parámetros cinemáticos del robot omnidireccional
R = 0.048  # Radio de la rueda (metros)
l1 = 0.097  # Distancia del centro al eje delantero
l2 = 0.109  # Distancia del centro al eje trasero
W = (1 / R) * np.array([
    [1, 1, -(l1 + l2)],
    [1, 1, (l1 + l2)],
    [1, -1, (l1 + l2)],
    [1, -1, -(l1 + l2)]
])
V_MAX = 250  # Velocidad máxima en mm/s
PWM_MAX = 100  # PWM máximo (%)

# Clase para simular el bus I2C
class FakeBus:
    def __init__(self):
        self.last_command = None
        
    def write_i2c_block_data(self, addr, reg, data):
        self.last_command = {
            'addr': hex(addr),
            'reg': hex(reg),
            'data': data,
            'timestamp': time.time()
        }
        # Mostrar valores PWM para cada motor
        motor_names = ['Motor Delantero Izquierdo', 'Motor Delantero Derecho', 
                      'Motor Trasero Derecho', 'Motor Trasero Izquierdo']
        print(f"[SIMULACIÓN I2C] Comando enviado:")
        print(f"  Dirección: {hex(addr)}, Registro: {hex(reg)}")
        for i, (name, pwm) in enumerate(zip(motor_names, data)):
            print(f"  {name}: PWM = {pwm:6.2f}")

# Inicializar bus I2C (real o simulado)
if not I2C_DISPONIBLE:
    bus = FakeBus()
else:
    print(f"[I2C] Usando bus I2C real en dirección {hex(DIRECCION_MOTORES)}")

# Configuración Flask y SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'robomesha-secret-key'
# Usar threading mode para compatibilidad con Python 3.13
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Estado del servidor
thread_lock = Lock()
devices = {}  # {device_id: {role, base_name, timestamp, sid}}
carritos_disponibles = {}  # {device_id: {hostname, timestamp, sid}}
device_id = None

def calcular_pwm(vx, vy, omega):
    """
    Calcula los valores PWM para los 4 motores basado en la cinemática omnidireccional
    vx: velocidad en x (mm/s)
    vy: velocidad en y (mm/s)
    omega: velocidad angular (rad/s)
    """
    V = np.array([vx, vy, omega])
    velocidades = np.dot(W, V)
    
    # Normalizar si excede el máximo
    factor_escala = np.max(np.abs(velocidades)) / V_MAX if np.max(np.abs(velocidades)) > V_MAX else 1
    if factor_escala > 1:
        velocidades /= factor_escala
    
    # Invertir motores 1 y 2 (según configuración original)
    velocidades[1] *= -1
    velocidades[2] *= -1
    
    # Convertir a PWM (-PWM_MAX a PWM_MAX)
    pwm = np.clip((velocidades / V_MAX) * PWM_MAX, -PWM_MAX, PWM_MAX)
    return [int(p) for p in pwm]

def enviar_pwm(vx, vy, omega):
    """
    Envía comandos PWM a los motores vía I2C
    vx, vy: velocidades en mm/s
    omega: velocidad angular en rad/s
    """
    pwm = calcular_pwm(vx, vy, omega)
    try:
        bus.write_i2c_block_data(DIRECCION_MOTORES, REG_VELOCIDAD_FIJA, pwm)
    except Exception as e:
        print(f"[ERROR] Error al enviar PWM: {e}")

def detener_motores():
    """Detiene todos los motores"""
    try:
        bus.write_i2c_block_data(DIRECCION_MOTORES, REG_VELOCIDAD_FIJA, [0, 0, 0, 0])
        print("[MOTORES] Todos los motores detenidos")
    except Exception as e:
        print(f"[ERROR] Error al detener motores: {e}")

def convertir_comando_frontend(x, y, rotation):
    """
    Convierte los valores del joystick del frontend a vx, vy, omega
    x, y: valores normalizados de -1 a 1 del joystick de movimiento
    rotation: valor normalizado de -1 a 1 del joystick de rotación
    """
    # Escalar a velocidad máxima (en mm/s)
    vx = x * V_MAX  # Movimiento en X
    vy = y * V_MAX  # Movimiento en Y
    
    # La rotación viene como valor normalizado, convertir a rad/s
    # Máxima rotación: aproximadamente 2 rad/s
    omega = rotation * 2.0  # rad/s
    
    return vx, vy, omega

# Eventos Socket.IO
@socketio.on('connect')
def handle_connect(auth):
    global device_id
    sid = request.sid
    with thread_lock:
        hostname = socket.gethostname()
        device_id = f"carrito_{hostname}_{uuid.uuid4().hex[:6]}"
        
        # Auto-registrar como carrito disponible
        carritos_disponibles[device_id] = {
            'hostname': hostname,
            'timestamp': time.time(),
            'sid': sid
        }
        devices[sid] = {
            'role': 'carrito',
            'base_name': hostname,
            'device_id': device_id,
            'timestamp': time.time()
        }
        
        print(f"[CONEXIÓN] Cliente conectado: {sid} - Carrito: {device_id}")
        emit('connected', {'device_id': device_id})
        
        # Enviar lista actualizada de dispositivos
        device_list = list(carritos_disponibles.keys())
        emit('device_list', {'devices': device_list})
        socketio.emit('device_list', {'devices': device_list})  # Broadcast a todos

@socketio.on('disconnect')
def handle_disconnect():
    with thread_lock:
        sid = request.sid
        # Remover dispositivo de la lista
        if sid in devices:
            dev_info = devices[sid]
            device_id_to_remove = dev_info.get('device_id')
            if device_id_to_remove in carritos_disponibles:
                del carritos_disponibles[device_id_to_remove]
            del devices[sid]
            print(f"[CONEXIÓN] Carrito {device_id_to_remove} desconectado")
        else:
            print(f"[CONEXIÓN] Cliente desconectado: {sid}")
        
        # Enviar lista actualizada
        socketio.emit('device_list', {'devices': list(carritos_disponibles.keys())})
    
    detener_motores()

@socketio.on('register')
def handle_register(data):
    """Registra un dispositivo (operador o carrito)"""
    with thread_lock:
        sid = request.sid
        role = data.get('role', 'operator')
        base_name = data.get('base_name', 'unknown')
        hostname = socket.gethostname()
        
        # Si es un carrito, crear ID único si no existe
        if role == 'carrito':
            if sid not in devices or not devices[sid].get('device_id'):
                new_device_id = f"carrito_{hostname}_{uuid.uuid4().hex[:6]}"
            else:
                new_device_id = devices[sid]['device_id']
            
            carritos_disponibles[new_device_id] = {
                'hostname': hostname,
                'timestamp': time.time(),
                'sid': sid
            }
        else:
            new_device_id = f"operator_{base_name}_{uuid.uuid4().hex[:6]}"
        
        devices[sid] = {
            'role': role,
            'base_name': base_name,
            'device_id': new_device_id,
            'timestamp': time.time()
        }
        
        print(f"[REGISTRO] Dispositivo registrado: {base_name} ({role}) - ID: {new_device_id} - SID: {sid}")
        
        # Enviar lista actualizada de dispositivos
        emit_device_list()

@socketio.on('list_devices')
def handle_list_devices():
    """Solicita la lista de dispositivos disponibles"""
    emit_device_list()

def emit_device_list():
    """Envía la lista de dispositivos a todos los clientes"""
    with thread_lock:
        device_list = list(carritos_disponibles.keys())
    
    socketio.emit('device_list', {'devices': device_list})
    print(f"[DEVICES] Lista de dispositivos: {device_list}")

@socketio.on('send_command')
def handle_send_command(data):
    """
    Recibe comandos de movimiento desde el frontend
    data: {target: device_id, payload: {type: 'movement', data: {x, y, rotation, timestamp}}}
    """
    target = data.get('target')
    payload = data.get('payload', {})
    
    if payload.get('type') == 'movement':
        movement_data = payload.get('data', {})
        x = movement_data.get('x', 0)
        y = movement_data.get('y', 0)
        rotation = movement_data.get('rotation', 0)
        
        # Convertir comandos del frontend a vx, vy, omega
        vx, vy, omega = convertir_comando_frontend(x, y, rotation)
        
        # Enviar a motores
        if abs(vx) > 0.1 or abs(vy) > 0.1 or abs(rotation) > 0.1:
            enviar_pwm(vx, vy, omega)
            print(f"[COMANDO] vx={vx:.1f} mm/s, vy={vy:.1f} mm/s, omega={omega:.3f} rad/s")
        else:
            detener_motores()
    else:
        print(f"[COMANDO] Tipo de comando desconocido: {payload.get('type')}")

def cerrar_todo(signal_received=None, frame=None):
    """Maneja la señal de cierre limpiamente"""
    print("\n[CERRANDO] Cerrando servidor...")
    detener_motores()
    sys.exit(0)

# Manejar señales de interrupción
signal.signal(signal.SIGINT, cerrar_todo)
signal.signal(signal.SIGTERM, cerrar_todo)

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Backend RoboMesha iniciando...")
    print("=" * 50)
    print(f"[I2C] Modo: {'REAL' if I2C_DISPONIBLE else 'SIMULACIÓN'}")
    print(f"[SERVIDOR] Escuchando en http://localhost:5000")
    print("=" * 50)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
