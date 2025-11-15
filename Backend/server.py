import socket
import threading

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit

# ----------------------------
# Configuración general
# ----------------------------
HTTP_PORT = 5000

MCAST_GRP = "239.255.100.100"
MCAST_PORT = 50000

SERVER_NAME = "FlaskBackend"  # nombre lógico del servidor para el DISCOVER


# ----------------------------
# Flask + Socket.IO
# ----------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret"  # cámbialo en producción
socketio = SocketIO(app, cors_allowed_origins="*")  # permite file:// y otros orígenes

# nombre_dispositivo -> sid
devices_by_name = {}
# sid -> nombre_dispositivo
names_by_sid = {}


# ----------------------------
# Endpoints HTTP (ejemplo)
# ----------------------------

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "server": SERVER_NAME})


@app.route("/command", methods=["POST"])
def send_command():
    """
    POST /command
    JSON:
    {
      "target": "NombreDelDispositivo",
      "payload": {...}   # JSON arbitrario
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    target = data.get("target")
    payload = data.get("payload")

    if not target or payload is None:
        return jsonify({"error": "Falta 'target' o 'payload'"}), 400

    sid = devices_by_name.get(target)
    if not sid:
        return jsonify({"error": f"Dispositivo '{target}' no conectado"}), 404

    # Enviamos evento 'command' solo al dispositivo objetivo
    socketio.emit("command", payload, room=sid)
    return jsonify({"status": "sent", "target": target})


# ----------------------------
# Socket.IO: eventos del dispositivo / web client
# ----------------------------

@socketio.on("connect")
def on_connect():
    print(f"[SOCKET] Cliente conectado, sid={request.sid}")


@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    name = names_by_sid.pop(sid, None)
    if name:
        devices_by_name.pop(name, None)
        print(f"[SOCKET] Dispositivo '{name}' desconectado (sid={sid})")
    else:
        print(f"[SOCKET] Cliente anónimo desconectado (sid={sid})")


@socketio.on("register")
def on_register(data):
    """
    El cliente (web o Python) manda:
    { "name": "RoboMesha-01" } o { "name": "WebClient-01" }
    """
    sid = request.sid
    name = (data or {}).get("name")

    if not name:
        emit("error", {"error": "Falta 'name' en register"})
        return

    devices_by_name[name] = sid
    names_by_sid[sid] = name

    print(f"[SOCKET] Cliente registrado: {name} (sid={sid})")
    emit("registered", {"status": "ok", "name": name})


@socketio.on("device_message")
def on_device_message(data):
    """
    Mensajes arbitrarios desde el dispositivo o cliente web.
    Ejemplo: estados, telemetría, logs, respuestas, etc.
    """
    sid = request.sid
    name = names_by_sid.get(sid, "anon")

    print(f"[SOCKET] device_message de {name}: {data}")


# ----------------------------
# Descubrimiento UDP (multicast) para el cliente Python
# ----------------------------

def discovery_responder():
    """
    Escucha mensajes:
      DISCOVER <nombre_cliente>
    Y responde:
      HELLO <SERVER_NAME> <HTTP_PORT>
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.bind(("", MCAST_PORT))

    mreq = socket.inet_aton(MCAST_GRP) + socket.inet_aton("0.0.0.0")
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print(f"[DISCOVERY] Escuchando en {MCAST_GRP}:{MCAST_PORT}")

    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode("utf-8", errors="ignore").strip()

        if msg.startswith("DISCOVER "):
            client_name = msg.split(" ", 1)[1]
            print(f"[DISCOVERY] Recibido DISCOVER de {client_name} desde {addr}")

            response = f"HELLO {SERVER_NAME} {HTTP_PORT}"
            sock.sendto(response.encode("utf-8"), addr)
            print(f"[DISCOVERY] Respondido: {response} a {addr}")


# ----------------------------
# main
# ----------------------------

def main():
    # Hilo para responder DISCOVER (para clientes Python)
    t = threading.Thread(target=discovery_responder, daemon=True)
    t.start()

    print(f"[HTTP] Iniciando Flask+SocketIO en 0.0.0.0:{HTTP_PORT}")
    socketio.run(app, host="0.0.0.0", port=HTTP_PORT)


if __name__ == "__main__":
    main()
