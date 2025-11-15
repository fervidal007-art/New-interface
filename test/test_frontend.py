#!/usr/bin/env python3
"""
Script de prueba para simular la recepción de comandos del frontend
"""
import socketio
import time

# Crear cliente Socket.IO
sio = socketio.Client()

@sio.event
def connect():
    print("✅ Conectado al servidor")
    # Registrar el dispositivo
    sio.emit('register', {'name': 'TestDevice-01'})

@sio.event
def disconnect():
    print("❌ Desconectado del servidor")

@sio.event
def registered(data):
    print(f"✅ Dispositivo registrado: {data}")

@sio.event
def command(data):
    print(f"📨 Comando recibido: {data}")

@sio.on('device_message')
def on_device_message(data):
    msg_type = data.get('type', 'unknown')
    
    if msg_type == 'movement':
        mov_data = data.get('data', {})
        print(f"🎮 Movimiento - X: {mov_data.get('x', 0):.2f}, Y: {mov_data.get('y', 0):.2f}, Rot: {mov_data.get('rotation', 0):.2f}")
    
    elif msg_type == 'telemetry':
        tel_data = data.get('data', {})
        print(f"📊 Telemetría - Velocidad: {tel_data.get('speed', 0)} km/h, Dirección: {tel_data.get('direction', 0)}°, Batería: {tel_data.get('battery', 0)}%")
    
    else:
        print(f"📩 Mensaje: {data}")

def main():
    try:
        print("🔄 Conectando a http://localhost:5000...")
        sio.connect('http://localhost:5000')
        
        # Mantener la conexión
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Deteniendo...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        sio.disconnect()

if __name__ == '__main__':
    main()


