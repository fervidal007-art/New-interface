import { useState, useEffect, useCallback, useMemo } from 'react';
import Header from './components/Header';
import SpeedDisplay from './components/SpeedDisplay';
import MovementButtons from './components/MovementButtons';
import RotationButtons from './components/RotationButtons';
import ControlPanel from './components/ControlPanel';
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
  const [mode, setMode] = useState('manual');
  const [movementInput, setMovementInput] = useState({ x: 0, y: 0 });
  const [rotationInput, setRotationInput] = useState({ x: 0, y: 0 });
  const [isConnected, setIsConnected] = useState(false);
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [conversations, setConversations] = useState({});
  const [isLogsOpen, setIsLogsOpen] = useState(false);
  const [movementLocked, setMovementLocked] = useState(false); // Bloqueo para cambio de movimiento
  const [speedLevel, setSpeedLevel] = useState(1); // Nivel de velocidad 1-5 (default: 1)

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

    socketService.on('connect', handleConnect);
    socketService.on('disconnect', handleDisconnect);
    socketService.on('device_list', handleDeviceList);
    socketService.on('conversation_message', handleConversationMessage);
    socketService.on('error', handleError);

    return () => {
      socketService.off('connect', handleConnect);
      socketService.off('disconnect', handleDisconnect);
      socketService.off('device_list', handleDeviceList);
      socketService.off('conversation_message', handleConversationMessage);
      socketService.off('error', handleError);
      socketService.disconnect();
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

  const handleMovement = (input) => {
    // Verificar si hay movimiento previo y no se ha presionado paro
    const hasPreviousMovement = movementInput.x !== 0 || movementInput.y !== 0;
    const hasNewMovement = input.x !== 0 || input.y !== 0;
    const isChangingDirection = hasPreviousMovement && hasNewMovement && 
                                (movementInput.x !== input.x || movementInput.y !== input.y);
    
    // Si está cambiando de dirección y está bloqueado, no permitir
    if (isChangingDirection && movementLocked) {
      console.log('⚠️ Debes presionar PARO antes de cambiar de dirección');
      return;
    }
    
    // Si se suelta el botón (todo en 0), NO hacer nada - mantener el último comando
    // Solo el botón de paro puede detener el movimiento
    if (!hasNewMovement) {
      return; // No actualizar estado ni enviar comando
    }
    
    // Si hay nuevo movimiento, activar el bloqueo y enviar comando UNA VEZ
    if (hasNewMovement) {
      setMovementLocked(true);
      setMovementInput(input);
      
      // Aplicar nivel de velocidad (1-5, donde 1=20%, 2=40%, ..., 5=100%)
      const speedMultiplier = speedLevel / 5;
      const scaledX = input.x * speedMultiplier;
      const scaledY = input.y * speedMultiplier;
      
      // Enviar comando SOLO cuando hay un nuevo movimiento (no repetir)
      if (isConnected) {
        socketService.sendMovement(selectedDevice, scaledX, scaledY, rotationInput.x);
      }
    }
  };

  const handleRotation = (input) => {
    // Si se suelta el botón (rotación en 0), NO hacer nada - mantener el último comando
    if (input.x === 0) {
      return; // No actualizar estado ni enviar comando
    }
    
    // Solo enviar comando cuando hay nueva rotación (no repetir)
    setRotationInput(input);

    setDirection(prev => {
      let newDir = prev + input.x * 5;
      if (newDir < 0) newDir += 360;
      if (newDir >= 360) newDir -= 360;
      return newDir;
    });

    // Aplicar nivel de velocidad a la rotación
    const speedMultiplier = speedLevel / 5;
    const scaledRotation = input.x * speedMultiplier;

    if (isConnected) {
      socketService.sendMovement(selectedDevice, movementInput.x, movementInput.y, scaledRotation);
    }
  };

  const handleEmergencyStop = () => {
    console.log('🚨 Paro de emergencia activado');
    
    // Primero resetear estado local INMEDIATAMENTE
    setMovementInput({ x: 0, y: 0 });
    setRotationInput({ x: 0, y: 0 });
    setSpeed(0);
    setMovementLocked(false); // Desbloquear después del paro
    
    // Luego enviar comando de paro al backend
    if (isConnected) {
      socketService.emergencyStop();
    }
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
          />
        </div>

        <div className="center-controls">
          <ControlPanel 
            mode={mode}
            onModeChange={setMode}
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
