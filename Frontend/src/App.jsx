import { useState, useEffect, useCallback, useMemo } from 'react';
import Header from './components/Header';
import SpeedDisplay from './components/SpeedDisplay';
import MovementButtons from './components/MovementButtons';
import RotationButtons from './components/RotationButtons';
import Stats from './components/Stats';
import LogsModal from './components/LogsModal';
import EmergencyButton from './components/EmergencyButton';
import SpeedControl from './components/SpeedControl';
import socketService from './utils/socket';

function App() {
  const [speed, setSpeed] = useState(0);
  const [direction, setDirection] = useState(45);
  const [gpsCoords] = useState({ lat: 41.40338, lng: 2.17403 });
  const [batteryLevel, setBatteryLevel] = useState(55);
  const [movementInput, setMovementInput] = useState({ x: 0, y: 0 });
  const [rotationInput, setRotationInput] = useState({ x: 0, y: 0 });
  const [isConnected, setIsConnected] = useState(false);
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [conversations, setConversations] = useState({});
  const [isLogsOpen, setIsLogsOpen] = useState(false);
  const [movementLocked, setMovementLocked] = useState(false);
  const [speedLevel, setSpeedLevel] = useState(1);
  const [emergencyStopActive, setEmergencyStopActive] = useState(false);

  const handleDeviceList = useCallback(
    (data = {}) => {
      const deviceList = Array.isArray(data.devices) ? data.devices : [];
      setDevices(deviceList);

      if (deviceList.length === 0) {
        setSelectedDevice('');
        return;
      }

      if (!deviceList.includes(selectedDevice)) {
        setSelectedDevice(deviceList[0]);
      }
    },
    [selectedDevice]
  );

  const handleConversationMessage = useCallback((msg = {}) => {
    const { device, direction, payload, ts, origin } = msg;
    if (!device) {
      return;
    }

    setConversations(prev => {
      const history = prev[device] ? [...prev[device]] : [];
      history.push({
        device,
        direction,
        payload,
        origin,
        ts: typeof ts === 'number' ? ts * 1000 : Date.now(),
      });
      if (history.length > 250) {
        history.shift();
      }
      return {
        ...prev,
        [device]: history,
      };
    });
  }, []);

  useEffect(() => {
    // Conectar al socket (es un singleton, así que es seguro llamarlo múltiples veces)
    socketService.connect();

    const handleConnect = () => {
      setIsConnected(true);
      console.log('✅ Conectado al servidor');
      socketService.requestDeviceList();
    };

    const handleDisconnect = () => {
      setIsConnected(false);
      console.log('⚠️ Desconectado del servidor');
    };

    const handleError = (err) => {
      console.error('Socket error:', err);
    };

    // Registrar listeners
    socketService.on('connect', handleConnect);
    socketService.on('disconnect', handleDisconnect);
    socketService.on('device_list', handleDeviceList);
    socketService.on('conversation_message', handleConversationMessage);
    socketService.on('error', handleError);

    return () => {
      // Limpiar listeners pero NO desconectar el socket
      // El socket es un singleton y puede ser usado por otros componentes
      // Solo desconectar cuando realmente se desmonte la app completa
      socketService.off('connect', handleConnect);
      socketService.off('disconnect', handleDisconnect);
      socketService.off('device_list', handleDeviceList);
      socketService.off('conversation_message', handleConversationMessage);
      socketService.off('error', handleError);
      // NO llamar a disconnect() aquí para evitar desconexiones en React StrictMode
    };
  }, [handleDeviceList, handleConversationMessage]);

  const handleConnect = () => {
    console.log('Attempting to connect...');
    socketService.connect();
  };

  const handleRefreshDevices = () => {
    console.log('Requesting device list...');
    socketService.requestDeviceList();
  };

  useEffect(() => {
    const magnitude = Math.sqrt(movementInput.x ** 2 + movementInput.y ** 2);
    const maxSpeed = 82;
    setSpeed(Math.round(magnitude * maxSpeed));
  }, [movementInput]);

  const handleMovement = (action) => {
    // Mapear acción a coordenadas para el estado local (para visualización)
    let x = 0;
    let y = 0;
    switch (action) {
      case 'adelante':
        y = 1;
        break;
      case 'atras':
        y = -1;
        break;
      case 'izquierda':
        x = -1;
        break;
      case 'derecha':
        x = 1;
        break;
      case 'diag_izq_arr':
        x = -0.707;
        y = 0.707;
        break;
      case 'diag_der_arr':
        x = 0.707;
        y = 0.707;
        break;
      case 'diag_izq_abj':
        x = -0.707;
        y = -0.707;
        break;
      case 'diag_der_abj':
        x = 0.707;
        y = -0.707;
        break;
      default:
        break;
    }
    
    // Verificar si hay movimiento previo
    const hasPreviousMovement = movementInput.x !== 0 || movementInput.y !== 0;
    const hasNewMovement = x !== 0 || y !== 0;
    const isChangingDirection = hasPreviousMovement && hasNewMovement && 
                                (movementInput.x !== x || movementInput.y !== y);
    
    // Si está cambiando de dirección y está bloqueado, no permitir
    if (isChangingDirection && movementLocked) {
      console.log('⚠️ Debes presionar PARO antes de cambiar de dirección');
      return;
    }
    
    // Si hay nuevo movimiento, enviar comando SIEMPRE (incluso si es el mismo botón)
    // IMPORTANTE: Enviar el comando ANTES de actualizar el estado para asegurar que siempre se ejecute
    if (hasNewMovement && isConnected) {
      socketService.sendCommand(action);
    }
    
    // Actualizar estado después de enviar el comando
    if (hasNewMovement) {
      setMovementLocked(true);
      setMovementInput({ x, y });
    }
  };

  const handleRotation = (action) => {
    // Mapear acción a rotación para el estado local (para visualización)
    let rotation = 0;
    switch (action) {
      case 'giro_izq':
        rotation = -1;
        break;
      case 'giro_der':
        rotation = 1;
        break;
      default:
        return;
    }
    
    setRotationInput({ x: rotation, y: 0 });

    setDirection(prev => {
      let newDir = prev + rotation * 5;
      if (newDir < 0) newDir += 360;
      if (newDir >= 360) newDir -= 360;
      return newDir;
    });

    // Enviar comando con el nombre de la acción
    if (isConnected) {
      socketService.sendCommand(action);
    }
  };

  const handleEmergencyStop = () => {
    console.log('🛑 PARO DE EMERGENCIA: Deteniendo motores');
    
    // Resetear estado local INMEDIATAMENTE
    setMovementInput({ x: 0, y: 0 });
    setRotationInput({ x: 0, y: 0 });
    setSpeed(0);
    setMovementLocked(false);
    
    // Enviar comando de paro al backend
    if (isConnected) {
      socketService.sendCommand('stop');
    }
    
    // El botón puede mostrar un estado visual temporal, pero no bloquea la interfaz
    // El estado emergencyStopActive solo se usa para indicación visual
    setEmergencyStopActive(true);
    // Desactivar el estado visual después de un breve momento
    setTimeout(() => {
      setEmergencyStopActive(false);
    }, 500);
  };

  const currentConversation = useMemo(() => {
    return selectedDevice ? conversations[selectedDevice] || [] : [];
  }, [conversations, selectedDevice]);

  return (
    <div className="app">
      <Header 
        batteryLevel={batteryLevel}
        isConnected={isConnected}
        onConnect={handleConnect}
        devices={devices}
        selectedDevice={selectedDevice}
        onDeviceChange={setSelectedDevice}
        onRefresh={handleRefreshDevices}
        onOpenLogs={() => setIsLogsOpen(true)}
        logsDisabled={!selectedDevice}
      />

      <div className="info-panel">
        <SpeedDisplay speed={speed} />
        <SpeedControl 
          speedLevel={speedLevel}
          onSpeedChange={setSpeedLevel}
          disabled={!isConnected || !selectedDevice}
        />
        <Stats 
          movementInput={movementInput}
          rotationInput={rotationInput}
        />
      </div>

      <div className="controls-panel">
        <div className="left-buttons">
          <MovementButtons 
            onMove={handleMovement}
            disabled={!isConnected || !selectedDevice}
            onEmergencyStop={handleEmergencyStop}
            emergencyStopActive={emergencyStopActive}
            activeMovement={movementInput}
          />
        </div>


        <div className="right-buttons">
          <RotationButtons 
            onRotate={handleRotation}
            disabled={!isConnected || !selectedDevice}
          />
        </div>
      </div>

      {isLogsOpen && (
        <LogsModal
          device={selectedDevice}
          messages={currentConversation}
          isConnected={isConnected}
          onClose={() => setIsLogsOpen(false)}
        />
      )}
    </div>
  );
}

export default App;
