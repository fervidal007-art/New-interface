import socket

MCAST_GRP = "239.255.100.100"
MCAST_PORT = 50000

def run_server(my_name: str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", MCAST_PORT))

    # Unirse al grupo multicast
    mreq = socket.inet_aton(MCAST_GRP) + socket.inet_aton("0.0.0.0")
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print(f"[SERVER] Soy {my_name}. Escuchando descubrimientos...\n")

    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode("utf-8", errors="ignore").strip()

        if msg.startswith("DISCOVER "):
            client_name = msg.split(" ", 1)[1]
            print(f"[SERVER] {client_name} me descubrió desde {addr}")

            response = f"HELLO {my_name}"
            sock.sendto(response.encode("utf-8"), addr)

            print(f"[SERVER] Respondí: {response}")


if __name__ == "__main__":
    # Cambia el nombre del dispositivo/robot
    run_server("RoboMesha-01")
