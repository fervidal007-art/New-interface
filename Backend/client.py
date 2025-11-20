import socket
import time
import json
import threading
import socketio  # python-socketio client

# ------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------
MCAST_GRP = "239.255.100.100"
MCAST_PORT = 50000

DEVICE_BASE_NAME = "RoboMesha"
ASSIGNED_NAME = None
DISCOVERY_TIMEOUT = 3.0          # Segundos máximo para descubrir servidor
RETRY_DELAY = 3.0


# ----------------------------------------------------
# DISCOVERY (autodetectar backend sin conocer IP)
# ----------------------------------------------------
def discover_server(timeout=DISCOVERY_TIMEOUT):
    """
    Envía:   DISCOVER <DEVICE_BASE_NAME>
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
            print("[DISCOVERY] No se encontró servidor.")
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

                print(f"[DISCOVERY] Servidor encontrado:")
                print(f"   Nombre: {server_name}")
                print(f"   IP:     {server_ip}")
                print(f"   Puerto: {http_port}")

                return server_ip, http_port, server_name


def wait_for_server():
    """
    Intenta descubrir servidores indefinidamente hasta que encuentre uno
    o hasta que el usuario cierre el cliente (/quit).
    """
    while not shutdown_event.is_set():
        result = discover_server()
        if result:
            return result
        print(f"[DISCOVERY] Ningún backend disponible. Reintentando en {RETRY_DELAY} s...")
        shutdown_event.wait(RETRY_DELAY)
    return None


# ----------------------------------------------------
# SOCKET.IO CLIENT
# ----------------------------------------------------
sio = socketio.Client(logger=False, engineio_logger=False, reconnection=False)
shutdown_event = threading.Event()
connect_lock = threading.Lock()


def pretty(obj):
    """Convierte JSON en string formateado."""
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except:
        return str(obj)


def current_name():
    return ASSIGNED_NAME or DEVICE_BASE_NAME


@sio.event
def connect():
    print("[SOCKET] Conectado al servidor, registrando...")
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


# 🔥 EVENTO: COMMAND
@sio.on("command")
def on_command(data):
    print("\n🔻🔻🔻  JSON RECIBIDO DEL SERVIDOR (command) 🔻🔻🔻")
    print(pretty(data))
    print("🔺🔺🔺 FIN JSON 🔺🔺🔺\n")

    # Enviar ACK
    ack = {
        "from": current_name(),
        "type": "ack",
        "received": data
    }
    sio.emit("device_message", ack)


# 🔥 Capturar TODOS LOS EVENTOS que el servidor mande
@sio.on("*")
def on_any_event(event, data):
    if event == "command":
        return  # ya lo manejamos arriba

    print(f"\n🟦 Evento recibido: '{event}'")
    print(pretty(data))
    print("🟦 Fin del evento\n")


# ----------------------------------------------------
# INPUT LOOP PARA ENVIAR MENSAJES
# ----------------------------------------------------
def input_loop():
    print("Escribe mensajes JSON o texto para enviar al backend.")
    print("Usa /quit para salir.")

    while True:
        try:
            text = input("> ").strip()
        except EOFError:
            break

        if text == "/quit":
            print("[CLIENT] Cerrando conexión...")
            shutdown_event.set()
            if sio.connected:
                sio.disconnect()
            break

        if not text:
            continue

        # Intentar enviar JSON literal
        try:
            payload = json.loads(text)
        except:
            payload = {"from": current_name(), "type": "message", "text": text}

        if sio.connected:
            sio.emit("device_message", payload)
            print("[CLIENT] JSON enviado:")
            print(pretty(payload))
        else:
            print("[CLIENT] No hay conexión activa; intenta nuevamente cuando se restablezca.")


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
                    print("[CONNECT] Ya existe una sesión activa, esperando eventos...")
                    connected = True
                else:
                    try:
                        sio.connect(url)
                        connected = True
                    except Exception as e:
                        print(f"[ERROR] No se pudo conectar al backend: {e}")

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

            print("[CLIENT] Conexión perdida. Buscando un nuevo servidor...")
            time.sleep(1.0)
    except KeyboardInterrupt:
        shutdown_event.set()
        print("\n[CLIENT] Interrumpido por usuario.")
    finally:
        shutdown_event.set()
        if sio.connected:
            sio.disconnect()
        input_thread.join(timeout=1)
        print("[CLIENT] Finalizado.")


if __name__ == "__main__":
    main()
