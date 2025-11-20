import atexit
import logging
import math
import socket
import struct
import threading
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from flask import Flask, request
from flask_socketio import SocketIO, emit

try:
    import smbus2 as smbus
except ImportError:  # pragma: no cover - entorno de desarrollo sin I2C
    smbus = None


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ============================================================================
# CONSTANTES DEL ROBOT
# ============================================================================

DIRECCION_MOTORES = 0x34
REG_PWM = 0x33
REG_ENCODERS = 0x3C
REG_BATERIA = 0x00

PULSOS_POR_REV = 1560
R = 0.048
L1 = 0.097
L2 = 0.109

W = (1 / R) * np.array(
    [
        [1, -1, (L1 + L2)],
        [1, 1, (L1 + L2)],
        [1, 1, -(L1 + L2)],
        [1, -1, -(L1 + L2)],
    ]
)

W_INV = np.linalg.pinv(W)

V_MAX = 50
PWM_MAX = 100
TIEMPO_MIN_I2C = 0.02


# ============================================================================
# Interfaces de hardware
# ============================================================================

class FakeBus:
    """Simulación mínima del bus I2C para ambientes sin hardware."""

    def write_i2c_block_data(self, addr, reg, data):
        logging.debug("[Simulación] write block -> addr=%s reg=%s data=%s", hex(addr), hex(reg), data)

    def write_byte_data(self, addr, reg, data):
        logging.debug("[Simulación] write byte -> addr=%s reg=%s data=%s", hex(addr), hex(reg), data)

    def read_i2c_block_data(self, addr, reg, length):
        logging.debug("[Simulación] read block -> addr=%s reg=%s len=%s", hex(addr), hex(reg), length)
        return [0] * length


class HardwareInterface:
    """Encapsula el acceso al bus I2C con protecciones básicas."""

    def __init__(self, bus_id: int = 1):
        self.simulated = smbus is None
        self._bus = None
        self._lock = threading.Lock()
        self._ultimo_i2c = 0.0
        self._bateria_cache = (0.0, 0.0)

        if not self.simulated:
            try:
                self._bus = smbus.SMBus(bus_id)
            except Exception as exc:  # pragma: no cover - solo en despliegue
                logging.warning("Fallo al abrir bus I2C, usando simulación: %s", exc)
                self.simulated = True

        if self.simulated:
            self._bus = FakeBus()

        self._init_driver()

    def _init_driver(self):
        try:
            self.write_byte(0x14, 3)
            time.sleep(0.1)
            self.write_byte(0x15, 0)
            time.sleep(0.1)
            logging.info("Controlador I2C inicializado")
        except Exception as exc:  # pragma: no cover - solo en hardware real con fallo
            logging.error("No se pudo inicializar el controlador I2C: %s", exc)

    def _esperar_intervalo(self):
        delta = time.time() - self._ultimo_i2c
        if delta < TIEMPO_MIN_I2C:
            time.sleep(TIEMPO_MIN_I2C - delta)
        self._ultimo_i2c = time.time()

    def write_block(self, registro: int, datos: List[int]) -> bool:
        with self._lock:
            self._esperar_intervalo()
            try:
                self._bus.write_i2c_block_data(DIRECCION_MOTORES, registro, datos)
                return True
            except Exception as exc:  # pragma: no cover - errores de hardware
                logging.error("Error escribiendo bloque I2C: %s", exc)
                return False

    def write_byte(self, registro: int, dato: int) -> bool:
        with self._lock:
            self._esperar_intervalo()
            try:
                self._bus.write_byte_data(DIRECCION_MOTORES, registro, dato)
                return True
            except Exception as exc:  # pragma: no cover
                logging.error("Error escribiendo byte I2C: %s", exc)
                return False

    def read_block(self, registro: int, longitud: int) -> Optional[List[int]]:
        with self._lock:
            self._esperar_intervalo()
            try:
                return list(self._bus.read_i2c_block_data(DIRECCION_MOTORES, registro, longitud))
            except Exception as exc:  # pragma: no cover
                logging.error("Error leyendo I2C: %s", exc)
                return None

    def stop_motors(self):
        self.write_block(REG_PWM, [0, 0, 0, 0])

    def read_battery(self) -> float:
        """Lee la batería con simple cache para evitar saturar el bus."""
        ts, valor = self._bateria_cache
        if time.time() - ts < 1.0:
            return valor or (12.0 if self.simulated else 0.0)

        datos = self.read_block(REG_BATERIA, 2)
        if not datos:
            return valor or (12.0 if self.simulated else 0.0)
        voltaje = (datos[0] + (datos[1] << 8)) / 1000.0
        if 5.0 < voltaje < 15.0:
            self._bateria_cache = (time.time(), voltaje)
            return voltaje
        return valor or (12.0 if self.simulated else 0.0)


# ============================================================================
# Componentes de control
# ============================================================================


class Odometria:
    """Sistema de odometría basado en los encoders de 4 ruedas."""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.habilitada = True
        self._tiempo = time.time()
        self._lock = threading.Lock()

    def habilitar(self):
        with self._lock:
            self.habilitada = True
            self.reset()

    def deshabilitar(self):
        with self._lock:
            self.habilitada = False

    def actualizar(self, vel_reales: List[float]) -> bool:
        with self._lock:
            if not self.habilitada:
                return False

            tiempo_actual = time.time()
            dt = tiempo_actual - self._tiempo
            if dt <= 0 or dt > 1.0:
                self._tiempo = tiempo_actual
                return False

            vel_robot = np.dot(W_INV, vel_reales)
            vx = -vel_robot[1]
            vy = -vel_robot[0]
            omega = vel_robot[2]

            if abs(vx) > 2.0 or abs(vy) > 2.0 or abs(omega) > 10.0:
                self._tiempo = tiempo_actual
                return False

            self.x += (vx * math.cos(self.theta) - vy * math.sin(self.theta)) * dt
            self.y += (vx * math.sin(self.theta) + vy * math.cos(self.theta)) * dt
            self.theta += omega * dt
            self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))
            self._tiempo = tiempo_actual
            return True

    def reset(self, x: float = 0.0, y: float = 0.0, theta: float = 0.0):
        with self._lock:
            self.x = x
            self.y = y
            self.theta = theta
            self._tiempo = time.time()

    def get_pose(self) -> Tuple[float, float, float]:
        with self._lock:
            return self.x, self.y, self.theta


class PIDController:
    """Controlador PID independiente para una rueda."""

    def __init__(self, kp: float = 1.2, ki: float = 0.4, kd: float = 0.05, limite: float = PWM_MAX):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.limite = limite
        self.error_anterior = 0.0
        self.integral = 0.0
        self._tiempo = time.time()

    def calcular(self, setpoint: float, medicion: float) -> float:
        tiempo_actual = time.time()
        dt = max(tiempo_actual - self._tiempo, 0.01)
        error = setpoint - medicion
        p = self.kp * error
        self.integral = np.clip(self.integral + error * dt, -30, 30)
        i = self.ki * self.integral
        d = self.kd * ((error - self.error_anterior) / dt)
        salida = np.clip(p + i + d, -self.limite, self.limite)
        self.error_anterior = error
        self._tiempo = tiempo_actual
        return salida

    def reset(self):
        self.error_anterior = 0.0
        self.integral = 0.0
        self._tiempo = time.time()


class ControladorVelocidad:
    """Controlador de 4 ruedas con PID y odometría integrada."""

    def __init__(self, hw: HardwareInterface):
        self.hw = hw
        self.pids = [PIDController() for _ in range(4)]
        self.odometria = Odometria()
        self._enc_anterior = [0, 0, 0, 0]
        self._tiempo = time.time()
        self.activo = True
        self.contador_lecturas = 0
        self._leer_encoders_inicial()

    def _leer_encoders_inicial(self):
        datos = self.hw.read_block(REG_ENCODERS, 16)
        if datos:
            self._enc_anterior = list(struct.unpack("iiii", bytes(datos)))

    def leer_velocidades_reales(self) -> List[float]:
        datos = self.hw.read_block(REG_ENCODERS, 16)
        if datos is None:
            self.contador_lecturas += 1
            return [0.0, 0.0, 0.0, 0.0]

        enc_actual = list(struct.unpack("iiii", bytes(datos)))
        tiempo_actual = time.time()
        dt = tiempo_actual - self._tiempo
        if dt <= 0:
            dt = 0.01
        elif dt > 1.0:
            self._enc_anterior = enc_actual
            self._tiempo = tiempo_actual
            return [0.0, 0.0, 0.0, 0.0]

        velocidades = []
        for i in range(4):
            delta = enc_actual[i] - self._enc_anterior[i]
            vel = (delta / dt) * (2 * math.pi / PULSOS_POR_REV)
            velocidades.append(vel if abs(vel) < 200 else 0.0)

        self._enc_anterior = enc_actual
        self._tiempo = tiempo_actual
        self.contador_lecturas += 1
        self.odometria.actualizar(velocidades)
        return velocidades

    def calcular_velocidades_deseadas(self, vx: float, vy: float, omega: float) -> np.ndarray:
        velocidades = np.dot(W, np.array([vx, vy, omega]))
        factor = np.max(np.abs(velocidades)) / V_MAX if np.max(np.abs(velocidades)) > V_MAX else 1
        if factor > 1:
            velocidades /= factor
        return velocidades

    def controlar(self, vx: float, vy: float, omega: float):
        if not self.activo:
            return [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]

        vel_deseadas = self.calcular_velocidades_deseadas(vx, vy, omega)
        vel_reales = self.leer_velocidades_reales()

        velocidades = vel_deseadas.copy()
        velocidades[1] *= -1
        velocidades[2] *= -1
        pwm_base = np.clip((velocidades / V_MAX) * PWM_MAX, -PWM_MAX, PWM_MAX)

        pwm_final = []
        for i in range(4):
            referencia = vel_deseadas[i]
            if i in (1, 2):
                referencia *= -1
            correccion = self.pids[i].calcular(referencia, vel_reales[i])
            pwm_final.append(int(np.clip(pwm_base[i] + correccion, -PWM_MAX, PWM_MAX)))

        return pwm_final, vel_deseadas.tolist(), vel_reales

    def enviar_pwm(self, pwm: List[int]) -> bool:
        return self.hw.write_block(REG_PWM, pwm)

    def reset(self):
        for pid in self.pids:
            pid.reset()
        self._leer_encoders_inicial()
        self._tiempo = time.time()
        if self.odometria.habilitada:
            self.odometria.reset()


# ============================================================================
# Robot controlado por sockets
# ============================================================================


class RobotDevice:
    """Gestiona el control del robot y expone una API simplificada."""

    def __init__(
        self,
        device_id: str,
        nombre: str,
        telemetry_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        log_callback: Optional[Callable[[str, str, Dict[str, Any], Optional[str]], None]] = None,
    ):
        self.device_id = device_id
        self.nombre = nombre
        self.hw = HardwareInterface()
        self.controlador = ControladorVelocidad(self.hw)
        self.telemetry_callback = telemetry_callback
        self.log_callback = log_callback
        self.command_lock = threading.Lock()
        self.status_lock = threading.Lock()
        self.running = True
        self.current_command = {
            "vx": 0.0,
            "vy": 0.0,
            "omega": 0.0,
            "timestamp": 0.0,
            "source": "system",
        }
        self.last_pwm = [0, 0, 0, 0]
        self.last_vel_des = [0.0, 0.0, 0.0, 0.0]
        self.last_vel_real = [0.0, 0.0, 0.0, 0.0]
        self.max_linear = 0.6
        self.max_lateral = 0.6
        self.max_angular = 3.0
        self.command_timeout = 0.6
        self.telemetry_period = 0.5
        self.sim_pose = {"x": 0.0, "y": 0.0, "theta": 0.0}
        self._sim_last = time.time()
        self._control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self._telemetry_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        self._control_thread.start()
        self._telemetry_thread.start()
        logging.info("Robot %s listo para recibir comandos", self.device_id)

    def _zero_command(self):
        return {
            "vx": 0.0,
            "vy": 0.0,
            "omega": 0.0,
            "timestamp": 0.0,
            "source": "system",
        }

    def _control_loop(self):
        while self.running:
            try:
                comando = self._get_active_command()
                if self.hw.simulated:
                    pwm, vel_des, vel_real = self._simulate_motion(
                        comando["vx"], comando["vy"], comando["omega"]
                    )
                else:
                    pwm, vel_des, vel_real = self.controlador.controlar(
                        comando["vx"], comando["vy"], comando["omega"]
                    )
                    if not self.controlador.enviar_pwm(pwm):
                        logging.warning("No se pudo enviar PWM; deteniendo motores por seguridad")
                        self.hw.stop_motors()

                with self.status_lock:
                    self.last_pwm = pwm
                    self.last_vel_des = vel_des
                    self.last_vel_real = vel_real

                time.sleep(0.05)
            except Exception as exc:  # pragma: no cover - errores inesperados de hardware
                logging.exception("Error en loop de control: %s", exc)
                self.hw.stop_motors()
                time.sleep(0.2)

    def _simulate_motion(self, vx: float, vy: float, omega: float):
        now = time.time()
        dt = max(now - self._sim_last, 0.05)
        self._sim_last = now

        theta = self.sim_pose["theta"]
        self.sim_pose["x"] += (vx * math.cos(theta) - vy * math.sin(theta)) * dt
        self.sim_pose["y"] += (vx * math.sin(theta) + vy * math.cos(theta)) * dt
        self.sim_pose["theta"] += omega * dt
        self.sim_pose["theta"] = math.atan2(
            math.sin(self.sim_pose["theta"]), math.cos(self.sim_pose["theta"])
        )

        vel_des = (
            self.controlador.calcular_velocidades_deseadas(vx, vy, omega).tolist()
            if self.controlador
            else [0.0, 0.0, 0.0, 0.0]
        )
        vel_adj = vel_des.copy()
        if len(vel_adj) >= 4:
            vel_adj[1] *= -1
            vel_adj[2] *= -1
        pwm = np.clip((np.array(vel_adj) / V_MAX) * PWM_MAX, -PWM_MAX, PWM_MAX).astype(int).tolist()

        return pwm, vel_des, vel_des  # en simulación asumimos seguimiento perfecto

    def _telemetry_loop(self):
        while self.running:
            estado = self.get_status()
            if self.telemetry_callback:
                self.telemetry_callback(estado)
            time.sleep(self.telemetry_period)

    def _get_active_command(self) -> Dict[str, Any]:
        with self.command_lock:
            comando = dict(self.current_command)
        if time.time() - comando["timestamp"] > self.command_timeout:
            return self._zero_command()
        return comando

    def set_joystick_command(self, x: float, y: float, rotation: float, requested_by: str = "operator"):
        vx = float(np.clip(y, -1, 1)) * self.max_linear
        vy = float(np.clip(x, -1, 1)) * self.max_lateral
        omega = float(np.clip(rotation, -1, 1)) * self.max_angular
        with self.command_lock:
            self.current_command = {
                "vx": vx,
                "vy": vy,
                "omega": omega,
                "timestamp": time.time(),
                "source": requested_by,
            }

        if self.log_callback:
            self.log_callback(
                "from_device",
                self.device_id,
                {
                    "event": "command_ack",
                    "vx": round(vx, 3),
                    "vy": round(vy, 3),
                    "omega": round(omega, 3),
                },
                origin=self.nombre,
            )

    def stop(self):
        with self.command_lock:
            self.current_command = self._zero_command()
        self.hw.stop_motors()

    def get_status(self) -> Dict[str, Any]:
        if self.hw.simulated:
            pose_tuple = (self.sim_pose["x"], self.sim_pose["y"], self.sim_pose["theta"])
        else:
            pose_tuple = self.controlador.odometria.get_pose()
        with self.status_lock:
            status = {
                "device": self.device_id,
                "timestamp": time.time(),
                "pose": {"x": pose_tuple[0], "y": pose_tuple[1], "theta": pose_tuple[2]},
                "pwm": self.last_pwm[:],
                "velocities": {
                    "desired": self.last_vel_des[:],
                    "real": self.last_vel_real[:],
                },
                "command": self._get_active_command(),
                "battery": self.hw.read_battery(),
                "simulated": self.hw.simulated,
            }
        return status

    def shutdown(self):
        logging.info("Apagando robot %s", self.device_id)
        self.running = False
        self.stop()
        self._control_thread.join(timeout=1.0)
        self._telemetry_thread.join(timeout=1.0)
        self.hw.stop_motors()


# ============================================================================
# Servidor Flask + Socket.IO
# ============================================================================


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

ROBOT_ID = f"carrito_{socket.gethostname()}"
clients: Dict[str, Dict[str, Any]] = {}
devices_registry: Dict[str, RobotDevice] = {}
conversation_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))


def broadcast_telemetry(data: Dict[str, Any]):
    """Envía lecturas periódicas al frontend."""
    socketio.emit("telemetry", data)


def push_conversation(direction: str, device: str, payload: Dict[str, Any], origin: Optional[str] = None):
    entry = {
        "device": device,
        "direction": direction,
        "payload": payload,
        "origin": origin or "backend",
        "ts": int(time.time()),
    }
    conversation_history[device].append(entry)
    socketio.emit("conversation_message", entry)


robot_device = RobotDevice(
    ROBOT_ID,
    nombre="Robot Mesha",
    telemetry_callback=broadcast_telemetry,
    log_callback=push_conversation,
)
devices_registry[ROBOT_ID] = robot_device


def current_device_list() -> Dict[str, Any]:
    return {
        "devices": list(devices_registry.keys()),
    }


@app.route("/health")
def health():
    status = robot_device.get_status()
    return {"status": "ok", "device": status}


@socketio.on("connect")
def handle_connect():
    clients[request.sid] = {
        "connected_at": time.time(),
        "role": "unknown",
        "name": f"client_{request.sid[:5]}",
    }
    emit("device_list", current_device_list())
    logging.info("Cliente conectado: %s", request.sid)


@socketio.on("disconnect")
def handle_disconnect():
    info = clients.pop(request.sid, None)
    logging.info("Cliente desconectado: %s (%s)", request.sid, info["name"] if info else "sin registro")


@socketio.on("register")
def handle_register(data):
    info = clients.get(request.sid)
    if not info:
        return
    role = data.get("role", "operator")
    base_name = data.get("base_name") or role
    info["role"] = role
    info["name"] = f"{role}_{base_name}_{uuid.uuid4().hex[:4]}"
    emit("device_list", current_device_list())
    logging.info("Cliente %s registrado como %s", request.sid, info["name"])


@socketio.on("list_devices")
def handle_list_devices():
    emit("device_list", current_device_list())


@socketio.on("send_command")
def handle_send_command(data):
    data = data or {}
    target = data.get("target")
    payload = data.get("payload", {})
    client = clients.get(request.sid, {"name": "cliente"})

    if target not in devices_registry:
        emit("error", {"message": f"Dispositivo {target} no disponible"})
        return

    dispositivo = devices_registry[target]
    push_conversation("from_operator", target, payload, origin=client["name"])

    tipo = payload.get("type")
    if tipo == "movement":
        movimiento = payload.get("data", {})
        x = movimiento.get("x", 0.0)
        y = movimiento.get("y", 0.0)
        rot = movimiento.get("rotation", 0.0)
        dispositivo.set_joystick_command(x, y, rot, requested_by=client["name"])
        emit(
            "command_status",
            {"status": "ok", "target": target, "type": tipo},
            room=request.sid,
        )
    elif tipo == "stop":
        dispositivo.stop()
        emit("command_status", {"status": "ok", "target": target, "type": "stop"}, room=request.sid)
    else:
        emit("error", {"message": f"Tipo de comando no soportado: {tipo}"})


def shutdown_server():
    for device in devices_registry.values():
        device.shutdown()


atexit.register(shutdown_server)


if __name__ == "__main__":
    logging.info("Iniciando servidor Socket.IO para %s", ROBOT_ID)
    socketio.run(app, host="0.0.0.0", port=5000)
