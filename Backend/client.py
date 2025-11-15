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

MY_NAME = "RoboMesha-Client02"   # Nombre con el que se registra
DISCOVERY_TIMEOUT = 3.0          # Segundos máximo para descubrir servidor


# ----------------------------------------------------
# DISCOVERY (autodetectar backend sin conocer IP)
# ----------------------------------------------------
def discover_server(timeout=DISCOVERY_TIMEOUT):
    """
    Envía:   DISCOVER <MY_NAME>
    Espera:  HELLO <SERVER_NAME> <HTTP_PORT>
    Devuelve: (server_ip, http_port, server_name) o None
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sock.settimeout(timeout)

    discover_msg = f"DISCOVER {MY_NAME}".encode("utf-8")
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


# ----------------------------------------------------
# SOCKET.IO CLIENT
# ----------------------------------------------------
sio = socketio.Client(logger=False, engineio_logger=False)


def pretty(obj):
    """Convierte JSON en string formateado."""
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except:
        return str(obj)


@sio.event
def connect():
    print("[SOCKET] Conectado al servidor, registrando...")
    sio.emit("register", {"name": MY_NAME})


@sio.event
def registered(data):
    print("[SOCKET] Registro confirmado:")
    print(pretty(data))


@sio.event
def disconnect():
    print("[SOCKET] Desconectado del backend.")


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
        "from": MY_NAME,
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
            sio.disconnect()
            break

        if not text:
            continue

        # Intentar enviar JSON literal
        try:
            payload = json.loads(text)
        except:
            payload = {"from": MY_NAME, "type": "message", "text": text}

        sio.emit("device_message", payload)
        print("[CLIENT] JSON enviado:")
        print(pretty(payload))


# ----------------------------------------------------
# PROGRAMA PRINCIPAL
# ----------------------------------------------------
def main():
    result = discover_server()
    if not result:
        print("No se pudo localizar el backend.")
        return

    server_ip, http_port, server_name = result
    url = f"http://{server_ip}:{http_port}"

    print(f"[CONNECT] Conectando a {url} ...")
    try:
        sio.connect(url)
    except Exception as e:
        print(f"[ERROR] No se pudo conectar al backend: {e}")
        return

    # Hilo para leer mensajes desde consola
    t = threading.Thread(target=input_loop, daemon=True)
    t.start()

    try:
        while sio.connected:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[CLIENT] Interrumpido por usuario.")
    finally:
        if sio.connected:
            sio.disconnect()
        print("[CLIENT] Finalizado.")


if __name__ == "__main__":
    main()
