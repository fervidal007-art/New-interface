import { useState, useEffect, useCallback, useMemo } from 'react';
import { Move, RotateCw } from 'lucide-react';
import Header from './components/Header';
import SpeedDisplay from './components/SpeedDisplay';
import Joystick from './components/Joystick';
import ControlPanel from './components/ControlPanel';
import Stats from './components/Stats';
import LogsModal from './components/LogsModal';
import EmergencyButton from './components/EmergencyButton';
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
    setMovementInput(input);

    if (isConnected) {
      socketService.sendMovement(selectedDevice, input.x, input.y, rotationInput.x);
    }
  };

  const handleRotation = (input) => {
    setRotationInput(input);

    setDirection(prev => {
      let newDir = prev + input.x * 5;
      if (newDir < 0) newDir += 360;
      if (newDir >= 360) newDir -= 360;
      return newDir;
    });

    if (isConnected) {
      socketService.sendMovement(selectedDevice, movementInput.x, movementInput.y, input.x);
    }
  };

  const handleEmergencyStop = () => {
    console.log('🚨 Paro de emergencia activado');
    socketService.emergencyStop();
    // Resetear joysticks visualmente
    setMovementInput({ x: 0, y: 0 });
    setRotationInput({ x: 0, y: 0 });
    setSpeed(0);
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

      <div className="main-content">
        <div className="left-panel">
          <SpeedDisplay speed={speed} />
          <Stats 
            movementInput={movementInput}
            rotationInput={rotationInput}
          />
        </div>

        <div className="center-panel" />

        <div className="right-panel" />
      </div>

      <div className="joystick-row">
        <Joystick 
          type="movement" 
          icon={Move}
          onMove={handleMovement}
        />

        <div className="center-controls">
          <ControlPanel 
            mode={mode}
            onModeChange={setMode}
          />
          <EmergencyButton onEmergencyStop={handleEmergencyStop} />
        </div>

        <Joystick 
          type="rotation" 
          icon={RotateCw}
          onMove={handleRotation}
        />
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
