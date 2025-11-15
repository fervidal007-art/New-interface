import socket
import threading
import json
import time

# --- Configuración ---
MCAST_GRP = "239.255.100.100"
MCAST_PORT = 50000

MY_NAME = "Ashton"   # Nombre de este lado


# --- Utilidades de red ---


def send_json(sock: socket.socket, obj: dict):
    data = json.dumps(obj, separators=(",", ":")) + "\n"
    sock.sendall(data.encode("utf-8"))


def recv_json_loop(sock: socket.socket, peer_label: str):
    f = sock.makefile("r", encoding="utf-8", newline="\n")
    try:
        for line in f:
            if line == "":
                # EOF duro: el otro lado cerró el socket
                print(f"[{peer_label}] EOF: el otro lado cerró la conexión.")
                break

            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print(f"[{peer_label}] Mensaje no es JSON válido:", line)
                continue

            print(f"[{peer_label}] JSON recibido:", obj)

    except ConnectionResetError as e:
        print(f"[{peer_label}] ConnectionResetError (red):", repr(e))
    except OSError as e:
        print(f"[{peer_label}] OSError en recepción:", repr(e))
    except Exception as e:
        print(f"[{peer_label}] Error inesperado en recepción:", repr(e))
    finally:
        print(f"[{peer_label}] Cerrando socket local.")
        try:
            sock.close()
        except Exception:
            pass


# --- Descubrimiento y conexión ---


def discover_server(timeout=3.0):
    """
    Envía DISCOVER <MY_NAME> por multicast y espera HELLO <name> <tcp_port>.
    Devuelve (ip_server, tcp_port, server_name) o None si no hay respuesta.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sock.settimeout(timeout)

    msg = f"DISCOVER {MY_NAME}".encode("utf-8")
    print(f"[CLIENT] Enviando descubrimiento como {MY_NAME} a {MCAST_GRP}:{MCAST_PORT}")
    sock.sendto(msg, (MCAST_GRP, MCAST_PORT))

    start = time.time()
    while True:
        remaining = timeout - (time.time() - start)
        if remaining <= 0:
            print("[CLIENT] Tiempo de descubrimiento agotado.")
            return None

        sock.settimeout(remaining)
        try:
            data, addr = sock.recvfrom(1024)
        except socket.timeout:
            print("[CLIENT] Sin respuesta.")
            return None

        resp = data.decode("utf-8", errors="ignore").strip()
        if resp.startswith("HELLO "):
            parts = resp.split(" ")
            if len(parts) == 3:
                server_name = parts[1]
                tcp_port = int(parts[2])
                server_ip = addr[0]

                print(f"[CLIENT] Servidor descubierto:")
                print(f"   Nombre: {server_name}")
                print(f"   IP:     {server_ip}")
                print(f"   TCP:    {tcp_port}")
                return server_ip, tcp_port, server_name


def connect_and_chat(ip, port, server_name):
    """
    Se conecta via TCP al servidor y mantiene comunicación JSON bidireccional.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    print(f"[CLIENT] Conectado a {server_name} en {ip}:{port}")

    # Hilo de escucha JSON
    t = threading.Thread(target=recv_json_loop, args=(sock, "CLIENT"), daemon=True)
    t.start()

    # Mensaje inicial
    send_json(sock, {"from": MY_NAME, "type": "greeting", "text": "hola, soy el cliente"})

    # Bucle interactivo para enviar mensajes JSON
    try:
        while True:
            text = input("CLIENT > ")
            if not text:
                print("[CLIENT] Cerrando conexión con el servidor...")
                sock.close()
                break

            msg = {
                "from": MY_NAME,
                "type": "message",
                "text": text,
            }
            send_json(sock, msg)
    except (EOFError, KeyboardInterrupt):
        print("\n[CLIENT] Saliendo del bucle de envío.")
        try:
            sock.close()
        except Exception:
            pass


def main():
    found = discover_server(timeout=3.0)
    if not found:
        print("[CLIENT] No se encontró servidor.")
        return

    ip, port, server_name = found
    connect_and_chat(ip, port, server_name)


if __name__ == "__main__":
    main()