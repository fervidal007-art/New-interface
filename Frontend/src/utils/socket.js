import { io } from 'socket.io-client';

// Configuración del servidor backend
const BACKEND_URL = 'http://localhost:5000';

class SocketService {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.deviceName = 'OmniCar-01';
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
      
      // Registrar el dispositivo
      this.socket.emit('register', { name: this.deviceName });
    });

    this.socket.on('registered', (data) => {
      console.log('Dispositivo registrado:', data);
    });

    this.socket.on('disconnect', () => {
      console.log('Desconectado del servidor');
      this.connected = false;
    });

    this.socket.on('command', (data) => {
      console.log('Comando recibido del servidor:', data);
    });

    this.socket.on('error', (error) => {
      console.error('Error de socket:', error);
    });

    return this.socket;
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.connected = false;
    }
  }

  // Enviar comandos de movimiento
  sendMovement(x, y, rotation) {
    if (!this.socket || !this.connected) {
      console.warn('Socket no conectado');
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

    this.socket.emit('device_message', payload);
  }

  // Enviar telemetría
  sendTelemetry(telemetry) {
    if (!this.socket || !this.connected) {
      console.warn('Socket no conectado');
      return;
    }

    const payload = {
      type: 'telemetry',
      data: telemetry
    };

    this.socket.emit('device_message', payload);
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

