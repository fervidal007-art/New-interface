import time
import uuid
import socket
import numpy as np
import firebase_admin
import signal
import sys
from firebase_admin import credentials, db

# Inicializar Firebase
cred = credentials.Certificate("robomesha-firebase-adminsdk-fbsvc-365a5d6215.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://robomesha-default-rtdb.firebaseio.com'
})

# IdentificaciÃ³n
hostname = socket.gethostname()
id_final = f"carrito_{hostname}_{uuid.uuid4().hex[:6]}"
carritos_ref = db.reference('carritos_disponibles')
comandos_ref = db.reference(f"comandos/{id_final}")

# Registrar disponibilidad
carritos_ref.child(id_final).set({
    "estado": "activo",
    "hostname": hostname,
    "timestamp": int(time.time())
})
print(f"Carrito registrado como: {id_final}")

# Motores (simulaciÃ³n si no hay smbus2)
try:
    import smbus2 as smbus
    bus = smbus.SMBus(1)
    # Probar si el bus responde
    bus.write_quick(0x34)
except Exception as e:
    print(f"[Simulacion] I2C no disponible: {e}")
    class FakeBus:
        def write_i2c_block_data(self, addr, reg, data):
            print(f"[Simulacion] I2C -> Addr: {hex(addr)}, Reg: {hex(reg)}, Data: {data}")
    bus = FakeBus()


DIRECCION_MOTORES = 0x34
REG_VELOCIDAD_FIJA = 0x33

R = 0.048
l1 = 0.097
l2 = 0.109
W = (1 / R) * np.array([
    [1, 1, -(l1 + l2)],
    [1, 1, (l1 + l2)],
    [1, -1, (l1 + l2)],
    [1, -1, -(l1 + l2)]
])
V_MAX = 250
PWM_MAX = 100

def calcular_pwm(vx, vy, omega):
    V = np.array([vx, vy, omega])
    velocidades = np.dot(W, V)
    factor_escala = np.max(np.abs(velocidades)) / 250 if np.max(np.abs(velocidades)) > 250 else 1
    if factor_escala > 1:
        velocidades /= factor_escala
    velocidades[1] *= -1
    velocidades[2] *= -1
    pwm = np.clip((velocidades / V_MAX) * PWM_MAX, -PWM_MAX, PWM_MAX)
    return [int(p) for p in pwm]

def enviar_pwm(vx, vy, omega):
    pwm = calcular_pwm(vx, vy, omega)
    bus.write_i2c_block_data(DIRECCION_MOTORES, REG_VELOCIDAD_FIJA, pwm)

def detener_motores():
    try:
        bus.write_i2c_block_data(DIRECCION_MOTORES, REG_VELOCIDAD_FIJA, [0, 0, 0, 0])
    except:
        print("Error al detener motores")

def cerrar_todo(signal_received=None, frame=None):
    detener_motores()
    print("Motores apagados.")
    try:
        comandos_ref.delete()
        carritos_ref.child(id_final).delete()

        terminar_actual = db.reference(f"terminar/{id_final}")
        if terminar_actual.get() is not None:
            terminar_actual.delete()

        print("Datos en Firebase eliminados.")
    except Exception as e:
        print(f"Error eliminando datos en Firebase: {e}")

    db.reference(f"estado_conexion/{id_final}").delete()
    sys.exit(0)

signal.signal(signal.SIGINT, cerrar_todo)
signal.signal(signal.SIGTERM, cerrar_todo)

terminar_ref = db.reference(f"terminar/{id_final}")


def escuchar_comandos():
    print("Escuchando comandos...")
    last_ts = 0
    last_ping = 0

    while True:
        now = int(time.time())

        # Enviar ping de conexion cada 1 segundo
        if now - last_ping >= 1:
            estado_ref = db.reference(f"estado_conexion/{id_final}")
            estado_ref.set({
                "por": id_final,
                "hostname": hostname,
                "timestamp": now
            })
            last_ping = now

        # Verificar senal de terminacion
        if terminar_ref.get() is True:
            print("Se recibio senal de terminacion desde el cliente.")
            cerrar_todo()

        # Procesar comandos
        data = comandos_ref.get()
        if isinstance(data, dict) and "timestamp" in data and data["timestamp"] != last_ts:
            vx = int(data.get("vx", 0))
            vy = int(data.get("vy", 0))
            w = int(data.get("w", 0))
            accion = data.get("accion", "detener")

            if accion == "mover":
                enviar_pwm(vx, vy, w)
                print(f"Moviendo: vx={vx}, vy={vy}, w={w}")
            else:
                detener_motores()
                print("Motores detenidos.")

            last_ts = data["timestamp"]

        time.sleep(0.1)


# Main
try:
    escuchar_comandos()
except KeyboardInterrupt:
    print("Interrumpido.")
    cerrar_todo()