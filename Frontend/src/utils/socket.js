import { io } from 'socket.io-client';

// Configuración dinámica del servidor backend
// Usa la misma IP que el frontend pero en el puerto 5000
// Si el frontend se accede desde la misma máquina que el backend, esto funciona perfectamente
const protocol = window.location.protocol;
const hostname = window.location.hostname;
const BACKEND_URL = `${protocol}//${hostname}:5000`;

// Nota: El backend escucha en 0.0.0.0:5000, lo que significa que acepta conexiones desde cualquier IP.
// El frontend usa window.location.hostname para detectar automáticamente la IP correcta.
// Esto funciona porque:
// - Si accedes desde http://10.42.0.1:5173 → se conecta a http://10.42.0.1:5000 ✅
// - Si accedes desde http://localhost:5173 → se conecta a http://localhost:5000 ✅
// - El backend en 0.0.0.0:5000 acepta conexiones desde ambas IPs ✅

class SocketService {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.deviceName = 'ControlPanel';
    this.listenersSetup = false; // Bandera para rastrear si los listeners básicos están configurados
    this.lastErrorTime = 0; // Para limitar la frecuencia de mensajes de error
    this.errorCooldown = 5000; // Mostrar error completo solo cada 5 segundos
  }

  connect() {
    // Si ya existe un socket conectado, reutilizarlo
    if (this.socket && this.socket.connected) {
      console.log('✅ Socket ya está conectado, reutilizando conexión');
      this.connected = true;
      return this.socket;
    }

    // Si ya existe un socket pero no está conectado, limpiarlo de forma segura
    if (this.socket) {
      const socketState = this.socket.io?.readyState || 'unknown';
      console.log(`🧹 Limpiando socket anterior (estado: ${socketState})`);
      
      // Remover listeners primero para evitar errores
      try {
        this.socket.removeAllListeners();
      } catch (e) {
        console.warn('Error al remover listeners:', e);
      }
      
      // Solo desconectar si el socket no está en proceso de conexión
      // Los estados de socket.io son: 'opening', 'open', 'closing', 'closed'
      if (socketState !== 'opening') {
        try {
          this.socket.disconnect();
        } catch (e) {
          console.warn('Error al desconectar socket:', e);
        }
      }
      
      this.socket = null;
      this.listenersSetup = false;
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
      forceNew: false, // Reutilizar conexiones cuando sea posible
    });

    // Solo configurar listeners básicos una vez por instancia de socket
    if (!this.listenersSetup) {
      this.socket.on('connect', () => {
        console.log('✅ Conectado al servidor:', this.socket.id);
        this.connected = true;
        
        // Registrar como operador
        this.socket.emit('register', { role: 'operator', base_name: this.deviceName });
      });

      this.socket.on('connect_error', (error) => {
        const errorMsg = error.message || 'Error desconocido';
        const now = Date.now();
        const timeSinceLastError = now - this.lastErrorTime;
        
        // Mostrar mensaje completo solo cada 5 segundos para evitar spam
        if (timeSinceLastError > this.errorCooldown) {
          console.error('❌ Error de conexión:', errorMsg);
          console.error(`   URL intentada: ${BACKEND_URL}`);
          console.error('   Verifica que el servidor backend esté corriendo:');
          console.error('   - Ejecuta: ./run_backend.sh');
          console.error('   - O manualmente: cd Backend && python3 server.py');
          this.lastErrorTime = now;
        } else {
          // Mensaje breve durante los intentos de reconexión
          console.warn('⚠️ Intentando reconectar... (el servidor backend no está disponible)');
        }
        this.connected = false;
      });

      this.socket.on('disconnect', (reason) => {
        if (reason !== 'io client disconnect') {
          console.warn('⚠️ Desconectado del servidor:', reason);
        }
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

      this.listenersSetup = true;
    }

    return this.socket;
  }

  disconnect(force = false) {
    if (this.socket) {
      if (force) {
        // Desconexión forzada: remover todos los listeners y desconectar
        this.socket.removeAllListeners();
        this.socket.disconnect();
        this.socket = null;
        this.listenersSetup = false;
      } else {
        // Desconexión suave: solo marcar como desconectado pero mantener la conexión
        // Esto evita desconexiones innecesarias en React StrictMode
        this.connected = false;
      }
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
