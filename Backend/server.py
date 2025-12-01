"""
Backend Optimizado para RoboMesha - Hiwonder Driver
Basado en documentación oficial: TankDemo.py y PDF de desarrollo.
"""
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import smbus
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
            self.bus = smbus.SMBus(I2C_BUS)
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

def izquierda():
    # Strafe Izquierda: M1(-), M2(+), M3(+), M4(-)
    v = [-VELOCIDAD, VELOCIDAD, VELOCIDAD, -VELOCIDAD]
    print(f">> IZQUIERDA {v}")
    driver.enviar_velocidad(v)

def derecha():
    # Strafe Derecha: M1(+), M2(-), M3(-), M4(+)
    v = [VELOCIDAD, -VELOCIDAD, -VELOCIDAD, VELOCIDAD]
    print(f">> DERECHA {v}")
    driver.enviar_velocidad(v)

def giro_izquierda():
    # Girar sobre su eje a la izquierda: Izquierdos(-), Derechos(+)
    v = [-VELOCIDAD, -VELOCIDAD, VELOCIDAD, VELOCIDAD]
    print(f">> GIRO IZQ {v}")
    driver.enviar_velocidad(v)

def giro_derecha():
    # Girar sobre su eje a la derecha: Izquierdos(+), Derechos(-)
    v = [VELOCIDAD, VELOCIDAD, -VELOCIDAD, -VELOCIDAD]
    print(f">> GIRO DER {v}")
    driver.enviar_velocidad(v)

# --- DIAGONALES (Solo mueven 2 ruedas) ---
def diagonal_izq_arriba():
    # M1(0), M2(+), M3(+), M4(0)
    v = [0, VELOCIDAD, VELOCIDAD, 0]
    print(f">> DIAG IZQ ARRIBA {v}")
    driver.enviar_velocidad(v)

def diagonal_der_arriba():
    # M1(+), M2(0), M3(0), M4(+)
    v = [VELOCIDAD, 0, 0, VELOCIDAD]
    print(f">> DIAG DER ARRIBA {v}")
    driver.enviar_velocidad(v)

def diagonal_izq_abajo():
    # M1(-), M2(0), M3(0), M4(-)
    v = [-VELOCIDAD, 0, 0, -VELOCIDAD]
    print(f">> DIAG IZQ ABAJO {v}")
    driver.enviar_velocidad(v)

def diagonal_der_abajo():
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

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = socketio.ASGIApp(sio, other_asgi_app=app_fastapi)

@sio.event
async def connect(sid, environ):
    print(f"Cliente conectado: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Cliente desconectado: {sid}")
    detener() # Seguridad: detener si se desconecta

@sio.event
async def command(sid, data):
    """
    Recibe el comando desde el botón de React.
    Data esperado: {"action": "adelante"} o {"action": "stop"}
    """
    accion = data.get("action")
    
    if accion in COMANDOS:
        # Ejecutar la función correspondiente
        COMANDOS[accion]() 
    else:
        print(f"Comando desconocido: {accion}")

if __name__ == '__main__':
    print("🚀 Iniciando servidor RoboMesha...")
    print("📡 Escuchando en puerto 5000")
    uvicorn.run(app, host='0.0.0.0', port=5000)