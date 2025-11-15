import socket
import threading
import json
import time

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit


# ----------------------------
# ConfiguraciÃ³n general
# ----------------------------
HTTP_PORT = 5000

MCAST_GRP = "239.255.100.100"
MCAST_PORT = 50000

SERVER_NAME = "FlaskBackend"  # nombre lÃ³gico del servidor para el DISCOVER


# ----------------------------
# Utilidades
# ----------------------------

def pretty(obj):
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


# ----------------------------
# Flask + Socket.IO
# ----------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret"  # cÃ¡mbialo en producciÃ³n
socketio = SocketIO(app, cors_allowed_origins="*")  # permite file:// y otros orÃ­genes

# nombre_dispositivo -> sid
devices_by_name = {}
# sid -> nombre_dispositivo
names_by_sid = {}
roles_by_sid = {}
operators = set()
assigned_names = set()


def generate_unique_name(base: str) -> str:
    label = (base or "Device").strip() or "Device"
    candidate = label
    suffix = 1
    while candidate in assigned_names:
        candidate = f"{label}-{suffix:02d}"
        suffix += 1
    assigned_names.add(candidate)
    return candidate


def release_name(name):
    if name:
        assigned_names.discard(name)


def broadcast_device_list():
    payload = {"devices": sorted(devices_by_name.keys())}
    for op_sid in list(operators):
        socketio.emit("device_list", payload, room=op_sid)


def broadcast_conversation(device, direction, payload, origin):
    if not device:
        return
    message = {
        "device": device,
        "direction": direction,
        "payload": payload,
        "origin": origin,
        "ts": time.time(),
    }
    for op_sid in list(operators):
        socketio.emit("conversation_message", message, room=op_sid)


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

    print("\n[HTTP] Enviando comando al dispositivo:", target)
    print(pretty(payload))

    # Enviamos evento 'command' solo al dispositivo objetivo
    socketio.emit("command", payload, room=sid)
    broadcast_conversation(target, "to_device", payload, origin="http")
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
    role = roles_by_sid.pop(sid, None)
    release_name(name)

    if role == "device" and name:
        devices_by_name.pop(name, None)
        broadcast_device_list()
        print(f"[SOCKET] Dispositivo '{name}' desconectado (sid={sid})")
    elif role == "operator":
        operators.discard(sid)
        print(f"[SOCKET] Operador '{name or sid}' desconectado (sid={sid})")
    else:
        print(f"[SOCKET] Cliente anónimo desconectado (sid={sid})")


@socketio.on("register")
def on_register(data):
    """
    Registro de clientes. El servidor asigna un nombre único y distingue
    entre roles 'device' (robots/equipos) y 'operator' (la interfaz web).
    """
    sid = request.sid
    payload = data or {}
    role = payload.get("role", "device")
    if role not in {"device", "operator"}:
        role = "device"

    base_name = payload.get("base_name") or payload.get("name")
    if role == "operator":
        base_name = base_name or "Operator"
    else:
        base_name = base_name or "Device"

    name = generate_unique_name(base_name)
    names_by_sid[sid] = name
    roles_by_sid[sid] = role

    if role == "device":
        devices_by_name[name] = sid
        broadcast_device_list()
    else:
        operators.add(sid)
        emit("device_list", {"devices": sorted(devices_by_name.keys())}, room=sid)

    print(f"\n[SOCKET] Cliente registrado: {name} (sid={sid}, role={role})")
    if payload:
        print("[SOCKET] Datos de registro:")
        print(pretty(payload))

    emit("registered", {"status": "ok", "name": name, "role": role})


@socketio.on("device_message")
def on_device_message(data):
    """
    Mensajes arbitrarios desde un dispositivo hacia el servidor.
    """
    sid = request.sid
    name = names_by_sid.get(sid, "anon")
    role = roles_by_sid.get(sid)

    if role != "device":
        emit("error", {"error": "Solo los dispositivos pueden emitir 'device_message'"}, room=sid)
        return

    print(f"\n📥 [SOCKET] device_message de '{name}' (sid={sid}):")
    print(pretty(data))
    print("📥 [SOCKET] fin mensaje\n")

    broadcast_conversation(name, "from_device", data, origin=name)


@socketio.on("list_devices")
def on_list_devices(_payload=None):
    """
    Devuelve al solicitante la lista de dispositivos registrados y listos.
    """
    sid = request.sid
    if roles_by_sid.get(sid) != "operator":
        emit("error", {"error": "Acceso denegado a list_devices"}, room=sid)
        return

    emit("device_list", {"devices": sorted(devices_by_name.keys())}, room=sid)


@socketio.on("send_command")
def on_send_command(data):
    """
    Permite que, por ejemplo, el cliente web solicite el envio de un comando
    hacia otro dispositivo registrado mediante {"target": "...", "payload": {...}}.
    """
    sid = request.sid
    sender = names_by_sid.get(sid, "anon")
    role = roles_by_sid.get(sid)

    if role != "operator":
        emit("error", {"error": "Solo un operador puede enviar comandos"}, room=sid)
        return

    target = (data or {}).get("target")
    payload = (data or {}).get("payload")

    if not target or payload is None:
        emit("error", {"error": "Falta 'target' o 'payload'"}, room=sid)
        return

    target_sid = devices_by_name.get(target)
    if not target_sid:
        emit("error", {"error": f"Dispositivo '{target}' no conectado"}, room=sid)
        return

    print(f"\n[SOCKET] '{sender}' envia comando a '{target}':")
    print(pretty(payload))
    print("[SOCKET] fin comando\n")

    socketio.emit("command", payload, room=target_sid)
    broadcast_conversation(target, "to_device", payload, origin=sender)

    emit("command_sent", {"target": target, "payload": payload}, room=sid)


@socketio.on("error")
def on_error_event(err):
    sid = request.sid
    name = names_by_sid.get(sid, "anon")
    print(f"\n[SOCKET] Error reportado por '{name}' (sid={sid}):")
    print(pretty(err))
    print()


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
