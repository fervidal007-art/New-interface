import json
import math
import queue
import socket
import struct
import threading
import time

import numpy as np
import socketio  # python-socketio client

try:
    import smbus2 as smbus
except Exception:  # pragma: no cover - fallback when smbus is not available
    smbus = None


# ------------------------------------------
# CONFIGURACION DE RED
# ------------------------------------------
MCAST_GRP = "239.255.100.100"
MCAST_PORT = 50000

DEVICE_BASE_NAME = "RoboMesha"
ASSIGNED_NAME = None
DISCOVERY_TIMEOUT = 3.0
RETRY_DELAY = 3.0


# ------------------------------------------
# CONFIGURACION DEL ROBOT
# ------------------------------------------
DIRECCION = 0x34
PULSOS_POR_REV = 1560
R = 0.048
L1 = 0.097
L2 = 0.109

W = (1 / R) * np.array([
    [1, -1, (L1 + L2)],
    [1, 1, (L1 + L2)],
    [1, 1, -(L1 + L2)],
    [1, -1, -(L1 + L2)],
])

W_INV = np.linalg.pinv(W)
V_MAX = 50.0
PWM_MAX = 100
TIEMPO_MIN_I2C = 0.02


# ------------------------------------------
# UTILIDADES GENERALES
# ------------------------------------------
def pretty(obj):
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


# ------------------------------------------
# BUS I2C Y MANEJO DE HARDWARE
# ------------------------------------------
def inicializar_bus():
    """Inicializa el bus I2C con manejo de errores."""
    if smbus is None:
        print("[I2C] smbus2 no disponible; modo simulacion.")
        return None

    try:
        bus_local = smbus.SMBus(1)
        bus_local.write_byte_data(DIRECCION, 0x14, 3)
        time.sleep(0.1)
        bus_local.write_byte_data(DIRECCION, 0x15, 0)
        time.sleep(0.1)
        print("[I2C] Bus inicializado correctamente.")
        return bus_local
    except Exception as exc:
        print(f"[I2C] Error al inicializar: {exc}")
        return None


bus = inicializar_bus()
bus_lock = threading.Lock()
ultimo_tiempo_i2c = time.time()


def esperar_i2c():
    global ultimo_tiempo_i2c
    tiempo_transcurrido = time.time() - ultimo_tiempo_i2c
    if tiempo_transcurrido < TIEMPO_MIN_I2C:
        time.sleep(TIEMPO_MIN_I2C - tiempo_transcurrido)
    ultimo_tiempo_i2c = time.time()


def escribir_i2c_seguro(registro, datos, max_intentos=2):
    if bus is None:
        return True

    esperar_i2c()
    for intento in range(max_intentos):
        try:
            with bus_lock:
                if isinstance(datos, list):
                    bus.write_i2c_block_data(DIRECCION, registro, datos)
                else:
                    bus.write_byte_data(DIRECCION, registro, datos)
            return True
        except Exception as exc:
            if intento == max_intentos - 1:
                print(f"[I2C] Error al escribir: {exc}")
                return False
            time.sleep(0.05)
    return False


def leer_i2c_seguro(registro, longitud, max_intentos=2):
    if bus is None:
        return [0] * longitud

    esperar_i2c()
    for intento in range(max_intentos):
        try:
            with bus_lock:
                return bus.read_i2c_block_data(DIRECCION, registro, longitud)
        except Exception as exc:
            if intento == max_intentos - 1:
                print(f"[I2C] Error al leer: {exc}")
                return None
            time.sleep(0.05)
    return None


def parar():
    for _ in range(3):
        if escribir_i2c_seguro(0x33, [0, 0, 0, 0]):
            return True
        time.sleep(0.1)
    return False


def leer_bateria():
    datos = leer_i2c_seguro(0x00, 2)
    if datos and len(datos) == 2:
        voltaje = (datos[0] + (datos[1] << 8)) / 1000.0
        if 5.0 < voltaje < 15.0:
            return voltaje
    return 0.0


# ------------------------------------------
# CLASES DE CONTROL
# ------------------------------------------
class Odometria:
    """Sistema de odometria usando encoders de 4 ruedas."""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.tiempo_anterior = time.time()
        self.habilitada = False

    def habilitar(self):
        if not self.habilitada:
            self.habilitada = True
            self.reset()

    def deshabilitar(self):
        self.habilitada = False

    def actualizar(self, vel_reales):
        if not self.habilitada:
            return False

        tiempo_actual = time.time()
        dt = tiempo_actual - self.tiempo_anterior

        if dt <= 0 or dt > 1.0:
            self.tiempo_anterior = tiempo_actual
            return False

        vel_robot = np.dot(W_INV, vel_reales)
        vx = -vel_robot[1]
        vy = -vel_robot[0]
        omega = vel_robot[2]

        if abs(vx) > 2.0 or abs(vy) > 2.0 or abs(omega) > 10.0:
            self.tiempo_anterior = tiempo_actual
            return False

        self.x += (vx * math.cos(self.theta) - vy * math.sin(self.theta)) * dt
        self.y += (vx * math.sin(self.theta) + vy * math.cos(self.theta)) * dt
        self.theta += omega * dt
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))
        self.tiempo_anterior = tiempo_actual
        return True

    def reset(self, x=0.0, y=0.0, theta=0.0):
        self.x = x
        self.y = y
        self.theta = theta
        self.tiempo_anterior = time.time()

    def get_pose(self):
        return self.x, self.y, self.theta


class PIDController:
    """Controlador PID para cada rueda."""

    def __init__(self, kp=1.2, ki=0.4, kd=0.05, limite=100):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.limite = limite
        self.error_anterior = 0.0
        self.integral = 0.0
        self.tiempo_anterior = time.time()

    def calcular(self, setpoint, medicion):
        tiempo_actual = time.time()
        dt = tiempo_actual - self.tiempo_anterior
        if dt <= 0:
            dt = 0.01

        error = setpoint - medicion
        p = self.kp * error
        self.integral += error * dt
        self.integral = float(np.clip(self.integral, -30, 30))
        i = self.ki * self.integral
        d = self.kd * ((error - self.error_anterior) / dt)
        salida = p + i + d
        salida = float(np.clip(salida, -self.limite, self.limite))
        self.error_anterior = error
        self.tiempo_anterior = tiempo_actual
        return salida

    def reset(self):
        self.error_anterior = 0.0
        self.integral = 0.0
        self.tiempo_anterior = time.time()


class ControladorVelocidad:
    """Control PID con odometria integrada."""

    def __init__(self):
        self.pids = [
            PIDController(),
            PIDController(),
            PIDController(),
            PIDController(),
        ]
        self.tiempo_anterior = time.time()
        self.activo = True
        self.contador_lecturas = 0
        self.odometria = Odometria()
        self.enc_anterior = self._leer_encoders_iniciales()

    def _leer_encoders_iniciales(self):
        datos = leer_i2c_seguro(0x3C, 16)
        if datos and len(datos) == 16:
            try:
                return list(struct.unpack("iiii", bytes(datos)))
            except Exception:
                pass
        return [0, 0, 0, 0]

    def leer_velocidades_reales(self):
        datos = leer_i2c_seguro(0x3C, 16)
        if datos is None or len(datos) != 16:
            self.activo = False
            return [0.0, 0.0, 0.0, 0.0]

        try:
            enc_actual = list(struct.unpack("iiii", bytes(datos)))
            tiempo_actual = time.time()
            dt = tiempo_actual - self.tiempo_anterior
            if dt <= 0:
                dt = 0.01
            elif dt > 1.0:
                self.enc_anterior = enc_actual
                self.tiempo_anterior = tiempo_actual
                return [0.0, 0.0, 0.0, 0.0]

            velocidades = []
            for i in range(4):
                delta = enc_actual[i] - self.enc_anterior[i]
                vel_rad_s = (delta / dt) * (2 * np.pi / PULSOS_POR_REV)
                if abs(vel_rad_s) > 200:
                    vel_rad_s = 0.0
                velocidades.append(float(vel_rad_s))

            self.enc_anterior = enc_actual
            self.tiempo_anterior = tiempo_actual
            self.contador_lecturas += 1
            self.odometria.actualizar(velocidades)
            return velocidades
        except Exception as exc:
            print(f"[ODOMETRIA] Error procesando encoders: {exc}")
            return [0.0, 0.0, 0.0, 0.0]

    def calcular_velocidades_deseadas(self, vx, vy, omega):
        velocidades = np.dot(W, np.array([vx, vy, omega]))
        max_abs = np.max(np.abs(velocidades))
        if max_abs > V_MAX:
            velocidades = velocidades / (max_abs / V_MAX)
        return velocidades

    def controlar(self, vx, vy, omega):
        if not self.activo:
            raise RuntimeError("Controlador desactivado por error de hardware")

        vel_deseadas = self.calcular_velocidades_deseadas(vx, vy, omega)
        vel_reales = self.leer_velocidades_reales()

        velocidades = vel_deseadas.copy()
        velocidades[1] *= -1
        velocidades[2] *= -1
        pwm_base = (velocidades / V_MAX) * PWM_MAX
        pwm_base = np.clip(pwm_base, -PWM_MAX, PWM_MAX)

        pwm_final = []
        for i in range(4):
            vel_objetivo = vel_deseadas[i]
            if i in (1, 2):
                vel_objetivo *= -1
            correccion = self.pids[i].calcular(vel_objetivo, vel_reales[i])
            pwm = int(np.clip(pwm_base[i] + correccion, -PWM_MAX, PWM_MAX))
            pwm_final.append(pwm)

        return pwm_final, vel_deseadas.tolist(), vel_reales

    def enviar_pwm(self, pwm):
        return escribir_i2c_seguro(0x33, [int(x) for x in pwm])

    def reset(self):
        for pid in self.pids:
            pid.reset()
        self.enc_anterior = self._leer_encoders_iniciales()
        self.tiempo_anterior = time.time()
        self.contador_lecturas = 0
        if self.odometria.habilitada:
            self.odometria.reset()


class RobotControlSystem:
    """Expone la logica del robot para comandos remotos."""

    def __init__(self):
        self.controlador = ControladorVelocidad()
        self.lock = threading.Lock()
        self.drive_interval = 0.1
        self.default_speed = 0.5

    def handle_command(self, payload):
        action = (payload or {}).get("action")
        if not action:
            raise ValueError("Falta 'action' en el comando")

        action = action.lower()
        if action == "move":
            return self._cmd_move(payload)
        if action == "stop":
            return self._cmd_stop()
        if action == "enable_odometry":
            return self._cmd_enable_odometry()
        if action == "disable_odometry":
            return self._cmd_disable_odometry()
        if action == "reset_pose":
            return self._cmd_reset_pose(payload)
        if action == "status":
            return self._cmd_status()
        if action == "home":
            return self._cmd_home(payload)
        if action == "update_pid":
            return self._cmd_update_pid(payload)
        if action == "set_speed":
            return self._cmd_set_speed(payload)
        raise ValueError(f"Accion desconocida: {action}")

    def _cmd_move(self, payload):
        vx = float(payload.get("vx", 0.0))
        vy = float(payload.get("vy", 0.0))
        omega = float(payload.get("omega", 0.0))
        duration = float(payload.get("duration", 1.0))
        if duration <= 0:
            duration = self.drive_interval

        muestras = max(1, int(duration / self.drive_interval))
        ultimo_sample = None
        with self.lock:
            for _ in range(muestras):
                pwm, vel_des, vel_real = self.controlador.controlar(vx, vy, omega)
                if not self.controlador.enviar_pwm(pwm):
                    raise RuntimeError("Fallo al enviar PWM")

                sample = {
                    "pwm": pwm,
                    "vel_deseadas": [round(v, 3) for v in vel_des],
                    "vel_reales": [round(v, 3) for v in vel_real],
                }
                if self.controlador.odometria.habilitada:
                    x, y, theta = self.controlador.odometria.get_pose()
                    sample["pose"] = {
                        "x": round(x, 4),
                        "y": round(y, 4),
                        "theta_deg": round(math.degrees(theta), 2),
                    }
                ultimo_sample = sample
                time.sleep(self.drive_interval)

            if payload.get("stop_after", True):
                parar()

        return {
            "status": "move_completed",
            "samples": ultimo_sample,
            "duration": duration,
        }

    def _cmd_stop(self):
        with self.lock:
            detenido = parar()
        return {"status": "stopped", "ok": detenido}

    def _cmd_enable_odometry(self):
        with self.lock:
            self.controlador.odometria.habilitar()
        return {"status": "odometry_enabled"}

    def _cmd_disable_odometry(self):
        with self.lock:
            self.controlador.odometria.deshabilitar()
        return {"status": "odometry_disabled"}

    def _cmd_reset_pose(self, payload):
        x = float(payload.get("x", 0.0))
        y = float(payload.get("y", 0.0))
        theta = math.radians(float(payload.get("theta_deg", 0.0)))
        with self.lock:
            self.controlador.odometria.reset(x, y, theta)
        return {"status": "pose_reset", "pose": self._pose_dict()}

    def _cmd_status(self):
        with self.lock:
            pose = self._pose_dict()
            pid = {
                "kp": self.controlador.pids[0].kp,
                "ki": self.controlador.pids[0].ki,
                "kd": self.controlador.pids[0].kd,
            }
            estado = {
                "odometry_enabled": self.controlador.odometria.habilitada,
                "lecturas": self.controlador.contador_lecturas,
                "bateria": leer_bateria(),
                "pose": pose,
                "pid": pid,
                "speed_profile": self.default_speed,
            }
        return estado

    def _cmd_home(self, payload):
        tolerancia = float(payload.get("tolerance", 0.1))
        timeout = float(payload.get("timeout", 60.0))
        if not self.controlador.odometria.habilitada:
            raise RuntimeError("Odometria deshabilitada, no se puede ir a HOME")

        tiempo_inicio = time.time()
        with self.lock:
            while time.time() - tiempo_inicio < timeout:
                x, y, theta = self.controlador.odometria.get_pose()
                distancia = math.sqrt(x * x + y * y)
                if distancia < tolerancia:
                    parar()
                    return {"status": "home", "pose": self._pose_dict()}

                velocidad = min(0.3, distancia * 0.5)
                angulo_objetivo = math.atan2(-y, -x)
                vx = velocidad * math.cos(angulo_objetivo - theta)
                vy = velocidad * math.sin(angulo_objetivo - theta)
                vx = float(np.clip(vx, -0.3, 0.3))
                vy = float(np.clip(vy, -0.3, 0.3))
                pwm, _, _ = self.controlador.controlar(vx, vy, 0.0)
                if not self.controlador.enviar_pwm(pwm):
                    raise RuntimeError("Error enviando PWM durante HOME")
                time.sleep(0.1)

            parar()
            return {"status": "timeout", "pose": self._pose_dict()}

    def _cmd_update_pid(self, payload):
        kp = payload.get("kp")
        ki = payload.get("ki")
        kd = payload.get("kd")
        if kp is None and ki is None and kd is None:
            raise ValueError("Se requiere al menos uno de kp/ki/kd")
        with self.lock:
            for pid in self.controlador.pids:
                if kp is not None:
                    pid.kp = float(kp)
                if ki is not None:
                    pid.ki = float(ki)
                if kd is not None:
                    pid.kd = float(kd)
            self.controlador.reset()
        return {
            "status": "pid_updated",
            "pid": {
                "kp": self.controlador.pids[0].kp,
                "ki": self.controlador.pids[0].ki,
                "kd": self.controlador.pids[0].kd,
            },
        }

    def _cmd_set_speed(self, payload):
        velocidad = float(payload.get("speed", self.default_speed))
        velocidad = float(np.clip(velocidad, 0.1, 0.9))
        self.default_speed = velocidad
        return {"status": "speed_profile_updated", "speed": velocidad}

    def _pose_dict(self):
        if not self.controlador.odometria.habilitada:
            return None
        x, y, theta = self.controlador.odometria.get_pose()
        return {
            "x": round(x, 4),
            "y": round(y, 4),
            "theta_deg": round(math.degrees(theta), 2),
        }


class CommandProcessor:
    """Procesa comandos en segundo plano para no bloquear el hilo de Socket.IO."""

    def __init__(self, robot):
        self.robot = robot
        self.queue = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def submit(self, command, callback):
        self.queue.put((command, callback))

    def stop(self):
        self.stop_event.set()
        self.queue.put((None, None))
        self.thread.join(timeout=1.0)

    def _worker(self):
        while not self.stop_event.is_set():
            command, callback = self.queue.get()
            if command is None:
                continue
            success = True
            result = None
            try:
                result = self.robot.handle_command(command)
            except Exception as exc:
                success = False
                result = {"error": str(exc)}
            if callback:
                callback(success, result)


robot_system = RobotControlSystem()
command_processor = CommandProcessor(robot_system)


# ----------------------------------------------------
# DISCOVERY (autodetectar backend sin conocer IP)
# ----------------------------------------------------
def discover_server(timeout=DISCOVERY_TIMEOUT):
    """
    Envia:   DISCOVER <DEVICE_BASE_NAME>
    Espera:  HELLO <SERVER_NAME> <HTTP_PORT>
    Devuelve: (server_ip, http_port, server_name) o None
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sock.settimeout(timeout)

    discover_msg = f"DISCOVER {DEVICE_BASE_NAME}".encode("utf-8")
    print(f"[DISCOVERY] Buscando servidor en {MCAST_GRP}:{MCAST_PORT} ...")
    sock.sendto(discover_msg, (MCAST_GRP, MCAST_PORT))

    start = time.time()
    while True:
        remaining = timeout - (time.time() - start)
        if remaining <= 0:
            print("[DISCOVERY] No se encontro servidor.")
            return None

        sock.settimeout(remaining)
        try:
            data, addr = sock.recvfrom(1024)
        except socket.timeout:
            print("[DISCOVERY] Sin respuesta.")
            return None

        msg = data.decode("utf-8", errors="ignore").strip()
        if msg.startswith("HELLO "):
            parts = msg.split(" ")
            if len(parts) == 3:
                server_name = parts[1]
                http_port = int(parts[2])
                server_ip = addr[0]
                print(f"[DISCOVERY] Servidor encontrado: {server_name} {server_ip}:{http_port}")
                return server_ip, http_port, server_name


def wait_for_server():
    while not shutdown_event.is_set():
        result = discover_server()
        if result:
            return result
        print(f"[DISCOVERY] Ningun backend disponible. Reintentando en {RETRY_DELAY} s...")
        shutdown_event.wait(RETRY_DELAY)
    return None


# ----------------------------------------------------
# SOCKET.IO CLIENT
# ----------------------------------------------------
sio = socketio.Client(logger=False, engineio_logger=False, reconnection=False)
shutdown_event = threading.Event()
connect_lock = threading.Lock()


def current_name():
    return ASSIGNED_NAME or DEVICE_BASE_NAME


@sio.event
def connect():
    print("[SOCKET] Conectado al servidor, registrando dispositivo...")
    sio.emit("register", {"role": "device", "base_name": DEVICE_BASE_NAME})


@sio.event
def registered(data):
    global ASSIGNED_NAME
    ASSIGNED_NAME = data.get("name") or ASSIGNED_NAME
    print("[SOCKET] Registro confirmado:")
    print(pretty(data))
    if ASSIGNED_NAME:
        print(f"[SOCKET] Nombre asignado por el servidor: {ASSIGNED_NAME}")


@sio.event
def disconnect():
    print("[SOCKET] Desconectado del backend.")
    if not shutdown_event.is_set():
        print("[SOCKET] Esperando nuevo servidor...")


@sio.event
def error(data):
    print("[SOCKET] Error recibido:")
    print(pretty(data))


@sio.on("command")
def on_command(data):
    print("\n[SOCKET] Comando recibido:")
    print(pretty(data))

    command_id = data.get("id") or f"{int(time.time() * 1000)}"
    ack = {
        "from": current_name(),
        "type": "ack",
        "command_id": command_id,
        "received": data,
        "status": "queued",
    }
    sio.emit("device_message", ack)

    def _done(success, result):
        payload = {
            "from": current_name(),
            "type": "command_result",
            "command_id": command_id,
            "success": success,
            "result": result,
        }
        sio.emit("device_message", payload)
        print("[ROBOT] Resultado enviado al servidor.")

    command_processor.submit(data, _done)


@sio.on("*")
def on_any_event(event, data):
    if event == "command":
        return
    print(f"\n[SOCKET] Evento '{event}' recibido:")
    print(pretty(data))


# ----------------------------------------------------
# INPUT LOOP PARA ENVIAR MENSAJES MANUALMENTE
# ----------------------------------------------------
def input_loop():
    print("Escribe JSON para enviar al backend. Usa /quit para salir.")
    while True:
        try:
            text = input("> ").strip()
        except EOFError:
            break

        if text == "/quit":
            print("[CLIENT] Cerrando conexion...")
            shutdown_event.set()
            if sio.connected:
                sio.disconnect()
            break

        if not text:
            continue

        try:
            payload = json.loads(text)
        except Exception:
            payload = {"from": current_name(), "type": "message", "text": text}

        if sio.connected:
            sio.emit("device_message", payload)
            print("[CLIENT] JSON enviado:")
            print(pretty(payload))
        else:
            print("[CLIENT] No hay conexion activa; intenta nuevamente cuando se restablezca.")


# ----------------------------------------------------
# PROGRAMA PRINCIPAL
# ----------------------------------------------------
def main():
    input_thread = threading.Thread(target=input_loop, daemon=True)
    input_thread.start()

    try:
        while not shutdown_event.is_set():
            found = wait_for_server()
            if not found:
                break

            server_ip, http_port, server_name = found
            url = f"http://{server_ip}:{http_port}"

            print(f"[CONNECT] Conectando a {url} ({server_name}) ...")
            connected = False
            with connect_lock:
                if shutdown_event.is_set():
                    break
                if sio.connected:
                    print("[CONNECT] Sesion ya activa, esperando eventos...")
                    connected = True
                else:
                    try:
                        sio.connect(url)
                        connected = True
                    except Exception as exc:
                        print(f"[ERROR] No se pudo conectar al backend: {exc}")

            if not connected:
                shutdown_event.wait(RETRY_DELAY)
                continue

            try:
                while sio.connected and not shutdown_event.is_set():
                    time.sleep(0.5)
            except KeyboardInterrupt:
                shutdown_event.set()
                break

            if shutdown_event.is_set():
                break

            print("[CLIENT] Conexion perdida. Buscando un nuevo servidor...")
            time.sleep(1.0)
    except KeyboardInterrupt:
        shutdown_event.set()
        print("\n[CLIENT] Interrumpido por usuario.")
    finally:
        shutdown_event.set()
        command_processor.stop()
        if sio.connected:
            sio.disconnect()
        input_thread.join(timeout=1)
        parar()
        print("[CLIENT] Finalizado.")


if __name__ == "__main__":
    main()
