import socket
import threading
import json

# --- Configuración ---
MCAST_GRP = "239.255.100.100"
MCAST_PORT = 50000

TCP_PORT = 60000           # Puerto TCP donde se mantendrá la conexión
MY_NAME = "RoboMesha-01"   # Nombre de este dispositivo


# --- Utilidades de red ---


def send_json(sock: socket.socket, obj: dict):
    """
    Envía un objeto JSON por un socket TCP, delimitado por '\n'.
    """
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

# --- Descubrimiento UDP (multicast) ---


def discovery_listener():
    """
    Escucha mensajes DISCOVER <nombre_cliente> por multicast y
    responde con HELLO <MY_NAME> <TCP_PORT>.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", MCAST_PORT))

    mreq = socket.inet_aton(MCAST_GRP) + socket.inet_aton("0.0.0.0")
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print(f"[SERVER] Descubrimiento: escuchando en {MCAST_GRP}:{MCAST_PORT}")

    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode("utf-8", errors="ignore").strip()

        if msg.startswith("DISCOVER "):
            client_name = msg.split(" ", 1)[1]
            print(f"[SERVER] Descubierto por {client_name} desde {addr}")

            response = f"HELLO {MY_NAME} {TCP_PORT}"
            sock.sendto(response.encode("utf-8"), addr)
            print(f"[SERVER] Respondido: {response}")


# --- Servidor TCP persistente ---


def tcp_server():
    """
    Servidor TCP simple: acepta una conexión y mantiene
    comunicación JSON bidireccional hasta que se cierre.
    """
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.bind(("", TCP_PORT))
    listen_sock.listen(1)
    print(f"[SERVER] TCP escuchando en 0.0.0.0:{TCP_PORT}")

    while True:
        conn, addr = listen_sock.accept()
        print(f"[SERVER] Cliente TCP conectado desde {addr}")

        # Hilo de escucha JSON
        t = threading.Thread(target=recv_json_loop, args=(conn, "SERVER"), daemon=True)
        t.start()

        # Ejemplo: saludo inicial en JSON
        send_json(conn, {"from": MY_NAME, "type": "greeting", "text": "hola, soy el servidor"})

        # Bucle interactivo para enviar JSON desde consola
        try:
            while True:
                text = input("SERVER > ")
                if not text:
                    # Enter vacío = cerrar conexión con este cliente
                    print("[SERVER] Cerrando conexión con el cliente...")
                    conn.close()
                    break

                msg = {
                    "from": MY_NAME,
                    "type": "message",
                    "text": text,
                }
                send_json(conn, msg)
        except (EOFError, KeyboardInterrupt):
            print("\n[SERVER] Saliendo del bucle de envío.")
            try:
                conn.close()
            except Exception:
                pass
            break

    listen_sock.close()
    print("[SERVER] TCP server finalizado.")


# --- main ---


def main():
    # Hilo para descubrimiento UDP
    t_disc = threading.Thread(target=discovery_listener, daemon=True)
    t_disc.start()

    # Servidor TCP (bloqueante en este hilo)
    tcp_server()


if __name__ == "__main__":
    main()
