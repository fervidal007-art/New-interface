import { io } from 'socket.io-client';

// Configuración dinámica del servidor backend
// Usa la misma IP que el frontend pero en el puerto 5000
const protocol = window.location.protocol;
const hostname = window.location.hostname;
const BACKEND_URL = `${protocol}//${hostname}:5000`;

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

    // Si ya existe un socket pero no está conectado, desconectarlo primero
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }

    console.log(`🔌 Intentando conectar a: ${BACKEND_URL}`);

    this.socket = io(BACKEND_URL, {
      autoConnect: true,
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: Infinity,
      timeout: 20000,
      transports: ['websocket', 'polling'],
    });

    this.socket.on('connect', () => {
      console.log('✅ Conectado al servidor:', this.socket.id);
      this.connected = true;
      
      // Registrar como operador
      this.socket.emit('register', { role: 'operator', base_name: this.deviceName });
    });

    this.socket.on('connect_error', (error) => {
      console.error('❌ Error de conexión:', error.message);
      console.error(`   URL intentada: ${BACKEND_URL}`);
      console.error('   Verifica que el servidor backend esté corriendo en el puerto 5000');
      this.connected = false;
    });

    this.socket.on('disconnect', (reason) => {
      console.warn('⚠️ Desconectado del servidor:', reason);
      this.connected = false;
    });

    this.socket.on('reconnect_attempt', (attemptNumber) => {
      console.log(`🔄 Intento de reconexión #${attemptNumber}...`);
    });

    this.socket.on('reconnect', (attemptNumber) => {
      console.log(`✅ Reconectado después de ${attemptNumber} intentos`);
      this.connected = true;
      this.socket.emit('register', { role: 'operator', base_name: this.deviceName });
    });

    this.socket.on('reconnect_failed', () => {
      console.error('❌ Falló la reconexión. El servidor puede estar inactivo.');
      this.connected = false;
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

  // Enviar comando con acción
  sendCommand(action) {
    if (!this.socket || !this.connected) {
      console.warn('Socket no conectado');
      return;
    }
    console.log(`📤 Enviando comando: ${action}`);
    this.socket.emit('command', { action });
  }

  // Paro de emergencia (mantener compatibilidad)
  emergencyStop() {
    this.sendCommand('stop');
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
