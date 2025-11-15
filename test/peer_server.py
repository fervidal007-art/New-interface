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