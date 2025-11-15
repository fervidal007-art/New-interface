import { io } from 'socket.io-client';

// Configuración del servidor backend
const BACKEND_URL = 'http://localhost:5000';

class SocketService {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.deviceName = 'ControlPanel';
  }

  connect() {
    if (this.socket && this.connected) {
      console.log('Socket ya está conectado');
      return this.socket;
    }

    this.socket = io(BACKEND_URL, {
      transports: ['websocket'],
      autoConnect: true,
    });

    this.socket.on('connect', () => {
      console.log('Conectado al servidor:', this.socket.id);
      this.connected = true;
      
      // Registrar como operador
      this.socket.emit('register', { role: 'operator', base_name: this.deviceName });
    });

    return this.socket;
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.connected = false;
    }
  }

  // Enviar comandos de movimiento a un target específico
  sendMovement(target, x, y, rotation) {
    if (!this.socket || !this.connected) {
      console.warn('Socket no conectado');
      return;
    }
    if (!target) {
      // console.warn('No hay un dispositivo seleccionado para enviar el comando');
      return;
    }

    const payload = {
      type: 'movement',
      data: {
        x: x,
        y: y,
        rotation: rotation,
        timestamp: Date.now()
      }
    };

    this.socket.emit('send_command', { target, payload });
  }

  // Solicitar la lista de dispositivos
  requestDeviceList() {
    if (!this.socket || !this.connected) {
      console.warn('Socket no conectado');
      return;
    }
    this.socket.emit('list_devices');
  }

  // Suscribirse a eventos personalizados
  on(event, callback) {
    if (this.socket) {
      this.socket.on(event, callback);
    }
  }

  // Desuscribirse de eventos
  off(event, callback) {
    if (this.socket) {
      this.socket.off(event, callback);
    }
  }

  // Obtener estado de conexión
  isConnected() {
    return this.connected;
  }
}

// Singleton
const socketService = new SocketService();

export default socketService;
